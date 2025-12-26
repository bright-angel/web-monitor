from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """用户模型"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # 密码重置token
    reset_token = db.Column(db.String(100), unique=True)
    reset_token_expires = db.Column(db.DateTime)
    
    # 关联
    websites = db.relationship('Website', backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    notification_channels = db.relationship('NotificationChannel', backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def generate_reset_token(self):
        """生成密码重置token"""
        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expires = datetime.now() + timedelta(hours=1)
        return self.reset_token
    
    def verify_reset_token(self, token):
        """验证重置token"""
        if self.reset_token != token:
            return False
        if self.reset_token_expires is None or datetime.now() > self.reset_token_expires:
            return False
        return True
    
    def clear_reset_token(self):
        """清除重置token"""
        self.reset_token = None
        self.reset_token_expires = None


class Website(db.Model):
    """网站监控模型"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    
    # 检查调度配置
    schedule_type = db.Column(db.String(20), default='interval')  # interval 或 cron
    check_interval = db.Column(db.Integer, default=60)  # 检查间隔（秒），用于interval模式
    cron_expression = db.Column(db.String(100))  # cron表达式，如 */5 * * * * (每5分钟)
    
    timeout = db.Column(db.Integer, default=30)  # 超时时间（秒）
    expected_status_code = db.Column(db.Integer, default=200)  # 期望的状态码
    is_active = db.Column(db.Boolean, default=True)  # 是否启用监控
    
    # 当前状态
    current_status = db.Column(db.String(20), default='unknown')  # online, offline, error, unknown
    last_status_code = db.Column(db.Integer)
    last_response_time = db.Column(db.Float)  # 响应时间（毫秒）
    last_check_time = db.Column(db.DateTime)
    last_error = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关联的通知渠道（多对多）
    notification_channels = db.relationship(
        'NotificationChannel',
        secondary='website_notification',
        backref=db.backref('websites', lazy='dynamic')
    )
    
    # 监控记录
    monitor_logs = db.relationship('MonitorLog', backref='website', lazy='dynamic', cascade='all, delete-orphan')


class NotificationChannel(db.Model):
    """通知渠道模型"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    channel_type = db.Column(db.String(20), nullable=False)  # dingtalk
    webhook_url = db.Column(db.String(500))
    secret = db.Column(db.String(200))  # 钉钉签名密钥
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)


# 网站与通知渠道的多对多关联表
website_notification = db.Table(
    'website_notification',
    db.Column('website_id', db.Integer, db.ForeignKey('website.id'), primary_key=True),
    db.Column('notification_channel_id', db.Integer, db.ForeignKey('notification_channel.id'), primary_key=True)
)


class MonitorLog(db.Model):
    """监控日志模型"""
    id = db.Column(db.Integer, primary_key=True)
    website_id = db.Column(db.Integer, db.ForeignKey('website.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # online, offline, error
    status_code = db.Column(db.Integer)
    response_time = db.Column(db.Float)  # 响应时间（毫秒）
    error_message = db.Column(db.Text)
    checked_at = db.Column(db.DateTime, default=datetime.now)
    
    # 是否触发了通知
    notification_sent = db.Column(db.Boolean, default=False)
