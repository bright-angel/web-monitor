from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, IntegerField, SelectField, SelectMultipleField, TextAreaField, RadioField
from wtforms.validators import DataRequired, Email, Length, EqualTo, URL, NumberRange, Optional, ValidationError, Regexp
from models import User
from flask import session


class LoginForm(FlaskForm):
    """登录表单"""
    username = StringField('用户名', validators=[DataRequired(message='请输入用户名')])
    password = PasswordField('密码', validators=[DataRequired(message='请输入密码')])
    captcha = StringField('验证码', validators=[DataRequired(message='请输入验证码')])
    remember_me = BooleanField('记住我')
    
    def validate_captcha(self, field):
        captcha_input = field.data.lower().strip()
        session_captcha = session.get('captcha')
        
        if not session_captcha:
            raise ValidationError('验证码已过期，请刷新页面重新获取')
        if captcha_input != session_captcha:
            raise ValidationError('验证码错误')


class ResetPasswordRequestForm(FlaskForm):
    """重置密码请求表单"""
    username = StringField('用户名', validators=[DataRequired(message='请输入用户名')])
    captcha = StringField('验证码', validators=[DataRequired(message='请输入验证码')])
    
    def validate_captcha(self, field):
        captcha_input = field.data.lower().strip()
        session_captcha = session.get('captcha')
        
        if not session_captcha:
            raise ValidationError('验证码已过期，请刷新页面重新获取')
        if captcha_input != session_captcha:
            raise ValidationError('验证码错误')


class RegisterForm(FlaskForm):
    """注册表单"""
    username = StringField('用户名', validators=[
        DataRequired(message='请输入用户名'),
        Length(min=3, max=20, message='用户名长度必须在3-20个字符之间')
    ])
    password = PasswordField('密码', validators=[
        DataRequired(message='请输入密码'),
        Length(min=6, message='密码长度至少6个字符')
    ])
    password2 = PasswordField('确认密码', validators=[
        DataRequired(message='请确认密码'),
        EqualTo('password', message='两次输入的密码不一致')
    ])
    captcha = StringField('验证码', validators=[DataRequired(message='请输入验证码')])
    
    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('用户名已存在')
    
    def validate_captcha(self, field):
        captcha_input = field.data.lower().strip()
        session_captcha = session.get('captcha')
        
        if not session_captcha:
            raise ValidationError('验证码已过期，请刷新页面重新获取')
        if captcha_input != session_captcha:
            raise ValidationError('验证码错误')


class WebsiteForm(FlaskForm):
    """网站表单"""
    name = StringField('网站名称', validators=[
        DataRequired(message='请输入网站名称'),
        Length(max=100, message='名称不能超过100个字符')
    ])
    url = StringField('网站URL', validators=[
        DataRequired(message='请输入网站URL'),
        URL(message='请输入有效的URL地址')
    ])
    
    # 调度类型
    schedule_type = RadioField('调度类型', choices=[
        ('interval', '固定间隔'),
        ('cron', 'Cron表达式')
    ], default='interval')
    
    check_interval = IntegerField('检查间隔(秒)', validators=[
        Optional(),
        NumberRange(min=30, max=86400, message='检查间隔必须在30秒到24小时之间')
    ], default=60)
    
    cron_expression = StringField('Cron表达式', validators=[
        Optional(),
        Length(max=100, message='Cron表达式不能超过100个字符')
    ])
    
    timeout = IntegerField('超时时间(秒)', validators=[
        DataRequired(message='请输入超时时间'),
        NumberRange(min=5, max=120, message='超时时间必须在5-120秒之间')
    ], default=30)
    expected_status_code = IntegerField('期望状态码', validators=[
        DataRequired(message='请输入期望状态码'),
        NumberRange(min=100, max=599, message='状态码必须在100-599之间')
    ], default=200)
    is_active = BooleanField('启用监控', default=True)
    notification_channels = SelectMultipleField('通知渠道', coerce=int, validators=[Optional()])
    
    def validate(self, extra_validators=None):
        if not super().validate(extra_validators):
            return False
        
        # 根据调度类型验证
        if self.schedule_type.data == 'interval':
            if not self.check_interval.data:
                self.check_interval.errors.append('请输入检查间隔')
                return False
        elif self.schedule_type.data == 'cron':
            if not self.cron_expression.data:
                self.cron_expression.errors.append('请输入Cron表达式')
                return False
            # 验证cron表达式格式
            if not self._validate_cron(self.cron_expression.data):
                self.cron_expression.errors.append('Cron表达式格式无效')
                return False
        return True
    
    def _validate_cron(self, cron_str):
        """验证cron表达式格式"""
        try:
            from apscheduler.triggers.cron import CronTrigger
            # 解析cron表达式 (5或6个字段)
            parts = cron_str.strip().split()
            if len(parts) == 5:
                # 标准cron: 分 时 日 月 周
                CronTrigger(minute=parts[0], hour=parts[1], day=parts[2], 
                           month=parts[3], day_of_week=parts[4])
            elif len(parts) == 6:
                # 扩展cron: 秒 分 时 日 月 周
                CronTrigger(second=parts[0], minute=parts[1], hour=parts[2],
                           day=parts[3], month=parts[4], day_of_week=parts[5])
            else:
                return False
            return True
        except:
            return False


class NotificationChannelForm(FlaskForm):
    """通知渠道表单"""
    name = StringField('渠道名称', validators=[
        DataRequired(message='请输入渠道名称'),
        Length(max=100, message='名称不能超过100个字符')
    ])
    channel_type = SelectField('渠道类型', choices=[
        ('dingtalk', '钉钉机器人')
    ], validators=[DataRequired()])
    webhook_url = StringField('Webhook URL', validators=[
        DataRequired(message='请输入Webhook URL'),
        URL(message='请输入有效的URL地址')
    ])
    secret = StringField('签名密钥(可选)', validators=[Optional(), Length(max=200)])
    is_active = BooleanField('启用', default=True)


class ChangePasswordForm(FlaskForm):
    """修改密码表单"""
    old_password = PasswordField('当前密码', validators=[DataRequired(message='请输入当前密码')])
    new_password = PasswordField('新密码', validators=[
        DataRequired(message='请输入新密码'),
        Length(min=6, message='密码长度至少6个字符')
    ])
    new_password2 = PasswordField('确认新密码', validators=[
        DataRequired(message='请确认新密码'),
        EqualTo('new_password', message='两次输入的新密码不一致')
    ])
