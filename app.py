from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import Config
from models import db, User, Website, NotificationChannel, MonitorLog
from forms import LoginForm, RegisterForm, WebsiteForm, NotificationChannelForm, ChangePasswordForm, ResetPasswordRequestForm
from monitor import check_website, init_scheduler, update_website_schedule
from datetime import datetime, timedelta
import psutil
import os
import secrets
from captcha import generate_captcha
from flask import send_file

app = Flask(__name__)
app.config.from_object(Config)

# 初始化扩展
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = '请先登录'
login_manager.login_message_category = 'warning'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ==================== 认证路由 ====================

@app.route('/captcha')
def captcha():
    """生成验证码"""
    text, img_buffer = generate_captcha()
    return send_file(img_buffer, mimetype='image/png')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            flash('登录成功！', 'success')
            return redirect(next_page or url_for('dashboard'))
        flash('用户名或密码错误', 'danger')
    
    return render_template('login.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if not app.config['ALLOW_REGISTRATION']:
        flash('注册功能已关闭', 'warning')
        return redirect(url_for('login'))
    
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('注册成功，请登录！', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('已退出登录', 'info')
    return redirect(url_for('login'))


# ==================== 仪表盘 ====================

@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    websites = current_user.websites.all()
    
    # 统计信息
    total = len(websites)
    online = sum(1 for w in websites if w.current_status == 'online')
    offline = sum(1 for w in websites if w.current_status == 'offline')
    error = sum(1 for w in websites if w.current_status == 'error')
    
    stats = {
        'total': total,
        'online': online,
        'offline': offline,
        'error': error
    }
    
    return render_template('dashboard.html', websites=websites, stats=stats)


# ==================== 网站管理 ====================

@app.route('/websites')
@login_required
def website_list():
    websites = current_user.websites.all()
    return render_template('websites/list.html', websites=websites)


@app.route('/websites/add', methods=['GET', 'POST'])
@login_required
def website_add():
    form = WebsiteForm()
    form.notification_channels.choices = [
        (c.id, c.name) for c in current_user.notification_channels.all()
    ]
    
    if form.validate_on_submit():
        website = Website(
            user_id=current_user.id,
            name=form.name.data,
            url=form.url.data,
            schedule_type=form.schedule_type.data,
            check_interval=form.check_interval.data if form.schedule_type.data == 'interval' else None,
            cron_expression=form.cron_expression.data if form.schedule_type.data == 'cron' else None,
            timeout=form.timeout.data,
            expected_status_code=form.expected_status_code.data,
            is_active=form.is_active.data
        )
        
        # 关联通知渠道
        if form.notification_channels.data:
            channels = NotificationChannel.query.filter(
                NotificationChannel.id.in_(form.notification_channels.data),
                NotificationChannel.user_id == current_user.id
            ).all()
            website.notification_channels = channels
        
        db.session.add(website)
        db.session.commit()
        
        # 更新调度配置
        update_website_schedule(app, website)
        
        flash('网站添加成功！', 'success')
        return redirect(url_for('website_list'))
    
    return render_template('websites/form.html', form=form, title='添加网站')


@app.route('/websites/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def website_edit(id):
    website = Website.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    form = WebsiteForm(obj=website)
    form.notification_channels.choices = [
        (c.id, c.name) for c in current_user.notification_channels.all()
    ]
    
    if request.method == 'GET':
        form.notification_channels.data = [c.id for c in website.notification_channels]
    
    if form.validate_on_submit():
        website.name = form.name.data
        website.url = form.url.data
        website.schedule_type = form.schedule_type.data
        website.check_interval = form.check_interval.data if form.schedule_type.data == 'interval' else None
        website.cron_expression = form.cron_expression.data if form.schedule_type.data == 'cron' else None
        website.timeout = form.timeout.data
        website.expected_status_code = form.expected_status_code.data
        website.is_active = form.is_active.data
        
        # 更新通知渠道
        if form.notification_channels.data:
            channels = NotificationChannel.query.filter(
                NotificationChannel.id.in_(form.notification_channels.data),
                NotificationChannel.user_id == current_user.id
            ).all()
            website.notification_channels = channels
        else:
            website.notification_channels = []
        
        db.session.commit()
        
        # 更新调度配置
        update_website_schedule(app, website)
        
        flash('网站更新成功！', 'success')
        return redirect(url_for('website_list'))
    
    return render_template('websites/form.html', form=form, title='编辑网站', website=website)


@app.route('/websites/<int:id>/delete', methods=['POST'])
@login_required
def website_delete(id):
    website = Website.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(website)
    db.session.commit()
    flash('网站已删除', 'success')
    return redirect(url_for('website_list'))


@app.route('/websites/<int:id>/check', methods=['POST'])
@login_required
def website_check(id):
    website = Website.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    result = check_website(website)
    return jsonify(result)


@app.route('/websites/<int:id>/logs')
@login_required
def website_logs(id):
    website = Website.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    page = request.args.get('page', 1, type=int)
    logs = website.monitor_logs.order_by(MonitorLog.checked_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('websites/logs.html', website=website, logs=logs)


# ==================== 通知渠道管理 ====================

@app.route('/channels')
@login_required
def channel_list():
    channels = current_user.notification_channels.all()
    return render_template('channels/list.html', channels=channels)


@app.route('/channels/add', methods=['GET', 'POST'])
@login_required
def channel_add():
    form = NotificationChannelForm()
    
    if form.validate_on_submit():
        channel = NotificationChannel(
            user_id=current_user.id,
            name=form.name.data,
            channel_type=form.channel_type.data,
            webhook_url=form.webhook_url.data,
            secret=form.secret.data or None,
            is_active=form.is_active.data
        )
        db.session.add(channel)
        db.session.commit()
        flash('通知渠道添加成功！', 'success')
        return redirect(url_for('channel_list'))
    
    return render_template('channels/form.html', form=form, title='添加通知渠道')


@app.route('/channels/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def channel_edit(id):
    channel = NotificationChannel.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    form = NotificationChannelForm(obj=channel)
    
    if form.validate_on_submit():
        channel.name = form.name.data
        channel.channel_type = form.channel_type.data
        channel.webhook_url = form.webhook_url.data
        channel.secret = form.secret.data or None
        channel.is_active = form.is_active.data
        db.session.commit()
        flash('通知渠道更新成功！', 'success')
        return redirect(url_for('channel_list'))
    
    return render_template('channels/form.html', form=form, title='编辑通知渠道', channel=channel)


@app.route('/channels/<int:id>/delete', methods=['POST'])
@login_required
def channel_delete(id):
    channel = NotificationChannel.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(channel)
    db.session.commit()
    flash('通知渠道已删除', 'success')
    return redirect(url_for('channel_list'))


@app.route('/channels/<int:id>/test', methods=['POST'])
@login_required
def channel_test(id):
    from notifier import DingTalkNotifier
    
    channel = NotificationChannel.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    if channel.channel_type == 'dingtalk':
        notifier = DingTalkNotifier(channel.webhook_url, channel.secret)
        success, message = notifier.send_message(
            '测试通知',
            '### 🔔 测试通知\n\n这是一条来自网站监控平台的测试消息。\n\n如果您收到此消息，说明通知渠道配置正确。'
        )
        return jsonify({'success': success, 'message': message})
    
    return jsonify({'success': False, 'message': '不支持的渠道类型'})


# ==================== 健康检测接口 ====================

@app.route('/health')
def health_check():
    """健康检测接口，用于心跳检测和Docker健康检查"""
    try:
        # 检查数据库连接
        db.session.execute(db.text('SELECT 1'))
        db_status = 'ok'
    except Exception as e:
        db_status = f'error: {str(e)}'
    
    # 获取系统资源使用情况
    try:
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        system_info = {
            'cpu_percent': psutil.cpu_percent(interval=0.1),
            'memory_percent': memory.percent,
            'memory_used_mb': round(memory.used / 1024 / 1024, 2),
            'disk_percent': disk.percent
        }
    except:
        system_info = {}
    
    # 统计信息
    try:
        total_websites = Website.query.count()
        active_websites = Website.query.filter_by(is_active=True).count()
        total_users = User.query.count()
    except:
        total_websites = 0
        active_websites = 0
        total_users = 0
    
    health_data = {
        'status': 'healthy' if db_status == 'ok' else 'unhealthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0',
        'database': db_status,
        'system': system_info,
        'stats': {
            'total_websites': total_websites,
            'active_websites': active_websites,
            'total_users': total_users
        }
    }
    
    status_code = 200 if db_status == 'ok' else 503
    return jsonify(health_data), status_code


@app.route('/health/live')
def liveness_check():
    """存活探针 - 用于Kubernetes/Docker"""
    return jsonify({'status': 'alive', 'timestamp': datetime.now().isoformat()}), 200


@app.route('/health/ready')
def readiness_check():
    """就绪探针 - 检查服务是否准备好接受流量"""
    try:
        db.session.execute(db.text('SELECT 1'))
        return jsonify({'status': 'ready', 'timestamp': datetime.now().isoformat()}), 200
    except Exception as e:
        return jsonify({'status': 'not_ready', 'error': str(e)}), 503


# ==================== API ====================

@app.route('/api/websites/status')
@login_required
def api_websites_status():
    websites = current_user.websites.all()
    data = []
    for w in websites:
        data.append({
            'id': w.id,
            'name': w.name,
            'url': w.url,
            'status': w.current_status,
            'status_code': w.last_status_code,
            'response_time': w.last_response_time,
            'last_check': w.last_check_time.isoformat() if w.last_check_time else None,
            'error': w.last_error
        })
    return jsonify(data)


@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    """修改密码"""
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.old_password.data):
            flash('当前密码错误', 'danger')
        else:
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash('密码修改成功！', 'success')
            return redirect(url_for('dashboard'))
    
    return render_template('change_password.html', form=form)


@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    """请求重置密码"""
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            reset_token = user.generate_reset_token()
            db.session.commit()
            # 在控制台输出重置链接
            reset_url = url_for('reset_password', token=reset_token, _external=True)
            print(f'密码重置链接: {reset_url}')
            flash('密码重置链接已生成，请查看控制台输出', 'info')
        else:
            flash('用户不存在', 'danger')
    
    return render_template('reset_password_request.html', form=form)


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """重置密码"""
    user = User.query.filter_by(reset_token=token).first()
    
    if not user or not user.verify_reset_token(token):
        flash('重置链接无效或已过期', 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        password = request.form.get('password', '').strip()
        password2 = request.form.get('password2', '').strip()
        
        if not password:
            flash('请输入新密码', 'danger')
        elif password != password2:
            flash('两次输入的密码不一致', 'danger')
        elif len(password) < 6:
            flash('密码长度至少6个字符', 'danger')
        else:
            user.set_password(password)
            user.clear_reset_token()
            db.session.commit()
            flash('密码重置成功，请登录！', 'success')
            return redirect(url_for('login'))
    
    return render_template('reset_password.html', token=token)


# ==================== 初始化 ====================

def init_db():
    with app.app_context():
        db.create_all()


if __name__ == '__main__':
    init_db()
    scheduler = init_scheduler(app)
    try:
        app.run(debug=True, use_reloader=False)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
