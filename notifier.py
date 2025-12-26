import time
import hmac
import hashlib
import base64
import urllib.parse
import requests
from datetime import datetime


class DingTalkNotifier:
    """钉钉通知服务"""
    
    def __init__(self, webhook_url, secret=None):
        self.webhook_url = webhook_url
        self.secret = secret
    
    def _generate_sign(self):
        """生成钉钉签名"""
        if not self.secret:
            return None, None
        
        timestamp = str(round(time.time() * 1000))
        secret_enc = self.secret.encode('utf-8')
        string_to_sign = '{}\n{}'.format(timestamp, self.secret)
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return timestamp, sign
    
    def send_message(self, title, content, is_at_all=False):
        """发送钉钉消息"""
        if not self.webhook_url:
            return False, "Webhook URL未配置"
        
        url = self.webhook_url
        timestamp, sign = self._generate_sign()
        
        if timestamp and sign:
            url = f"{self.webhook_url}&timestamp={timestamp}&sign={sign}"
        
        headers = {'Content-Type': 'application/json'}
        data = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": content
            },
            "at": {
                "isAtAll": is_at_all
            }
        }
        
        try:
            response = requests.post(url, json=data, headers=headers, timeout=10)
            result = response.json()
            if result.get('errcode') == 0:
                return True, "发送成功"
            else:
                return False, result.get('errmsg', '发送失败')
        except Exception as e:
            return False, str(e)


def send_status_change_notification(website, old_status, new_status, channels):
    """发送网站状态变化通知"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 状态emoji和颜色
    status_info = {
        'online': ('✅', '正常'),
        'offline': ('❌', '不可用'),
        'error': ('⚠️', '异常'),
        'unknown': ('❓', '未知')
    }
    
    old_emoji, old_text = status_info.get(old_status, ('❓', '未知'))
    new_emoji, new_text = status_info.get(new_status, ('❓', '未知'))
    
    title = f"网站状态变化: {website.name}"
    
    content = f"""### {new_emoji} 网站状态变化通知

**网站名称**: {website.name}

**网站地址**: {website.url}

**状态变化**: {old_emoji} {old_text} → {new_emoji} {new_text}

**当前状态码**: {website.last_status_code or 'N/A'}

**响应时间**: {website.last_response_time:.2f}ms

**检查时间**: {now}
"""
    
    if website.last_error:
        content += f"\n**错误信息**: {website.last_error}"
    
    results = []
    for channel in channels:
        if channel.channel_type == 'dingtalk' and channel.is_active:
            notifier = DingTalkNotifier(channel.webhook_url, channel.secret)
            success, message = notifier.send_message(title, content)
            results.append({
                'channel': channel.name,
                'success': success,
                'message': message
            })
    
    return results


def send_status_code_change_notification(website, old_code, new_code, channels):
    """发送状态码变化通知"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    title = f"网站状态码变化: {website.name}"
    
    content = f"""### ⚡ 网站状态码变化通知

**网站名称**: {website.name}

**网站地址**: {website.url}

**状态码变化**: {old_code or 'N/A'} → {new_code}

**当前状态**: {website.current_status}

**响应时间**: {website.last_response_time:.2f}ms

**检查时间**: {now}
"""
    
    results = []
    for channel in channels:
        if channel.channel_type == 'dingtalk' and channel.is_active:
            notifier = DingTalkNotifier(channel.webhook_url, channel.secret)
            success, message = notifier.send_message(title, content)
            results.append({
                'channel': channel.name,
                'success': success,
                'message': message
            })
    
    return results
