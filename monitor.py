import requests
import time
import psutil
from datetime import datetime
from models import db, Website, MonitorLog
from notifier import send_status_change_notification, send_status_code_change_notification, DingTalkNotifier


def check_website(website):
    """检查单个网站的可用性"""
    old_status = website.current_status
    old_status_code = website.last_status_code
    
    start_time = time.time()
    
    try:
        response = requests.get(
            website.url,
            timeout=website.timeout,
            headers={
                'User-Agent': 'WebMonitor/1.0'
            },
            allow_redirects=True
        )
        
        end_time = time.time()
        response_time = (end_time - start_time) * 1000  # 转换为毫秒
        status_code = response.status_code
        
        # 判断状态
        if status_code == website.expected_status_code:
            new_status = 'online'
            error_message = None
        else:
            new_status = 'error'
            error_message = f"期望状态码 {website.expected_status_code}，实际返回 {status_code}"
        
    except requests.exceptions.Timeout:
        end_time = time.time()
        response_time = (end_time - start_time) * 1000
        new_status = 'offline'
        status_code = None
        error_message = "请求超时"
        
    except requests.exceptions.ConnectionError:
        end_time = time.time()
        response_time = (end_time - start_time) * 1000
        new_status = 'offline'
        status_code = None
        error_message = "连接失败"
        
    except Exception as e:
        end_time = time.time()
        response_time = (end_time - start_time) * 1000
        new_status = 'error'
        status_code = None
        error_message = str(e)
    
    # 更新网站状态
    website.current_status = new_status
    website.last_status_code = status_code
    website.last_response_time = response_time
    website.last_check_time = datetime.now()
    website.last_error = error_message
    
    # 创建监控日志
    log = MonitorLog(
        website_id=website.id,
        status=new_status,
        status_code=status_code,
        response_time=response_time,
        error_message=error_message
    )
    db.session.add(log)
    
    # 检查是否需要发送通知
    notification_sent = False
    
    # 状态变化通知（排除首次检查的unknown状态）
    if old_status != 'unknown' and old_status != new_status:
        if website.notification_channels:
            send_status_change_notification(website, old_status, new_status, website.notification_channels)
            notification_sent = True
    
    # 状态码变化通知（仅当有状态码时）
    if old_status_code is not None and status_code is not None and old_status_code != status_code:
        if website.notification_channels:
            send_status_code_change_notification(website, old_status_code, status_code, website.notification_channels)
            notification_sent = True
    
    log.notification_sent = notification_sent
    db.session.commit()
    
    return {
        'status': new_status,
        'status_code': status_code,
        'response_time': response_time,
        'error': error_message
    }


def check_all_websites(app):
    """检查所有需要检查的网站（仅用于interval模式的网站）"""
    with app.app_context():
        # 只检查interval模式的网站
        websites = Website.query.filter_by(is_active=True, schedule_type='interval').all()
        
        for website in websites:
            # 检查是否到达检查时间
            if website.last_check_time is None:
                should_check = True
            else:
                elapsed = (datetime.now() - website.last_check_time).total_seconds()
                should_check = elapsed >= (website.check_interval or 60)
            
            if should_check:
                try:
                    check_website(website)
                except Exception as e:
                    print(f"检查网站 {website.name} 时出错: {e}")


def check_single_website(app, website_id):
    """检查单个网站（用于cron调度）"""
    with app.app_context():
        website = Website.query.get(website_id)
        if website and website.is_active:
            try:
                check_website(website)
            except Exception as e:
                print(f"检查网站 {website.name} 时出错: {e}")


def parse_cron_expression(cron_str):
    """解析cron表达式为APScheduler参数"""
    parts = cron_str.strip().split()
    if len(parts) == 5:
        # 标准cron: 分 时 日 月 周
        return {
            'minute': parts[0],
            'hour': parts[1],
            'day': parts[2],
            'month': parts[3],
            'day_of_week': parts[4]
        }
    elif len(parts) == 6:
        # 扩展cron: 秒 分 时 日 月 周
        return {
            'second': parts[0],
            'minute': parts[1],
            'hour': parts[2],
            'day': parts[3],
            'month': parts[4],
            'day_of_week': parts[5]
        }
    return None


def init_scheduler(app):
    """初始化调度器"""
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    
    scheduler = BackgroundScheduler()
    
    # 每10秒检查一次interval模式的网站
    scheduler.add_job(
        func=check_all_websites,
        trigger='interval',
        seconds=10,
        args=[app],
        id='check_interval_websites',
        replace_existing=True
    )
    
    # 为cron模式的网站创建单独的调度任务
    with app.app_context():
        cron_websites = Website.query.filter_by(is_active=True, schedule_type='cron').all()
        for website in cron_websites:
            if website.cron_expression:
                add_cron_job_for_website(scheduler, app, website)
    
    # 平台自查任务
    if app.config.get('SELF_CHECK_ENABLED', True):
        cron_expr = app.config.get('SELF_CHECK_CRON', '0 * * * *')
        cron_params = parse_cron_expression(cron_expr)
        if cron_params:
            scheduler.add_job(
                func=platform_self_check,
                trigger=CronTrigger(**cron_params),
                args=[app],
                id='platform_self_check',
                replace_existing=True
            )
        # 启动后立即执行一次自查
        scheduler.add_job(
            func=platform_self_check,
            trigger='date',
            run_date=datetime.now(),
            args=[app],
            id='platform_self_check_init'
        )
    
    scheduler.start()
    
    # 保存scheduler引用到app
    app.scheduler = scheduler
    
    return scheduler


def add_cron_job_for_website(scheduler, app, website):
    """为网站添加cron调度任务"""
    from apscheduler.triggers.cron import CronTrigger
    
    cron_params = parse_cron_expression(website.cron_expression)
    if cron_params:
        job_id = f'website_cron_{website.id}'
        scheduler.add_job(
            func=check_single_website,
            trigger=CronTrigger(**cron_params),
            args=[app, website.id],
            id=job_id,
            replace_existing=True
        )
        print(f"[调度器] 添加网站cron任务: {website.name} ({website.cron_expression})")


def remove_cron_job_for_website(scheduler, website_id):
    """移除网站的cron调度任务"""
    job_id = f'website_cron_{website_id}'
    try:
        scheduler.remove_job(job_id)
        print(f"[调度器] 移除网站cron任务: {job_id}")
    except:
        pass


def update_website_schedule(app, website):
    """更新网站的调度配置"""
    scheduler = getattr(app, 'scheduler', None)
    if not scheduler:
        return
    
    # 先移除旧的cron任务
    remove_cron_job_for_website(scheduler, website.id)
    
    # 如果是cron模式且启用，添加新任务
    if website.is_active and website.schedule_type == 'cron' and website.cron_expression:
        add_cron_job_for_website(scheduler, app, website)


def platform_self_check(app):
    """平台自身状态自查"""
    with app.app_context():
        webhook = app.config.get('DINGTALK_WEBHOOK')
        secret = app.config.get('DINGTALK_SECRET')
        platform_name = app.config.get('PLATFORM_NAME', '网站监控平台')
        
        if not webhook:
            print(f"[{datetime.now()}] 平台自查: 未配置钉钉Webhook，跳过通知")
            return
        
        # 收集平台状态信息
        status_info = collect_platform_status(app)
        
        # 判断是否有异常
        has_issues = (
            status_info['db_status'] != 'ok' or
            status_info['cpu_percent'] > 90 or
            status_info['memory_percent'] > 90 or
            status_info['disk_percent'] > 90 or
            status_info['offline_count'] > 0
        )
        
        # 构建通知内容
        if has_issues:
            title = f"⚠️ {platform_name} 状态异常"
            status_emoji = "⚠️"
        else:
            title = f"✅ {platform_name} 运行正常"
            status_emoji = "✅"
        
        content = f"""### {status_emoji} 平台自查报告

**检查时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

#### 系统资源
- **CPU使用率**: {status_info['cpu_percent']:.1f}%
- **内存使用率**: {status_info['memory_percent']:.1f}%
- **磁盘使用率**: {status_info['disk_percent']:.1f}%

#### 数据库状态
- **连接状态**: {'✅ 正常' if status_info['db_status'] == 'ok' else '❌ 异常'}

#### 监控统计
- **用户数**: {status_info['user_count']}
- **监控网站数**: {status_info['website_count']}
- **正常网站**: {status_info['online_count']}
- **异常网站**: {status_info['offline_count'] + status_info['error_count']}
"""
        
        if has_issues:
            content += "\n---\n\n**请及时检查并处理异常情况！**"
        
        # 发送通知
        notifier = DingTalkNotifier(webhook, secret)
        success, message = notifier.send_message(title, content)
        
        if success:
            print(f"[{datetime.now()}] 平台自查通知发送成功")
        else:
            print(f"[{datetime.now()}] 平台自查通知发送失败: {message}")


def collect_platform_status(app):
    """收集平台状态信息"""
    from models import User, Website
    
    # 系统资源
    try:
        cpu_percent = psutil.cpu_percent(interval=0.5)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
    except:
        cpu_percent = 0
        memory = type('obj', (object,), {'percent': 0})()
        disk = type('obj', (object,), {'percent': 0})()
    
    # 数据库状态
    try:
        db.session.execute(db.text('SELECT 1'))
        db_status = 'ok'
    except:
        db_status = 'error'
    
    # 统计信息
    try:
        user_count = User.query.count()
        website_count = Website.query.count()
        online_count = Website.query.filter_by(current_status='online').count()
        offline_count = Website.query.filter_by(current_status='offline').count()
        error_count = Website.query.filter_by(current_status='error').count()
    except:
        user_count = website_count = online_count = offline_count = error_count = 0
    
    return {
        'cpu_percent': cpu_percent,
        'memory_percent': memory.percent,
        'disk_percent': disk.percent,
        'db_status': db_status,
        'user_count': user_count,
        'website_count': website_count,
        'online_count': online_count,
        'offline_count': offline_count,
        'error_count': error_count
    }
