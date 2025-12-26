import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-me'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///monitor.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 是否开放注册
    ALLOW_REGISTRATION = os.environ.get('ALLOW_REGISTRATION', 'true').lower() == 'true'
    
    # 钉钉配置（用于平台自查通知）
    DINGTALK_WEBHOOK = os.environ.get('DINGTALK_WEBHOOK')
    DINGTALK_SECRET = os.environ.get('DINGTALK_SECRET')
    
    # 平台自查配置
    SELF_CHECK_ENABLED = os.environ.get('SELF_CHECK_ENABLED', 'true').lower() == 'true'
    SELF_CHECK_CRON = os.environ.get('SELF_CHECK_CRON', '0 * * * *')  # 默认每小时整点
    PLATFORM_NAME = os.environ.get('PLATFORM_NAME', '网站监控平台')
