# 网站监控平台

一个基于Flask的网站监控平台，支持多用户管理、网站状态监控、实时通知和日志记录。

## 🚀 功能特性

### 核心功能
- **用户管理**: 完整的用户注册、登录、密码重置系统
- **网站监控**: 支持HTTP/HTTPS网站状态监控
- **智能调度**: 支持定时间隔和Cron表达式两种调度方式
- **实时通知**: 支持钉钉等Webhook通知渠道
- **日志记录**: 详细的监控日志和历史记录
- **健康检查**: 提供完整的健康检查和监控接口

### 高级特性
- **响应时间监控**: 记录网站响应时间
- **状态码验证**: 支持期望状态码检查
- **超时配置**: 可自定义请求超时时间
- **批量操作**: 支持网站批量启停、删除
- **多用户支持**: 用户数据隔离，安全可靠

## 📋 系统要求

- Python 3.8+
- SQLite (默认) 或其他SQL数据库
- 4GB+ RAM (推荐)
- 稳定的网络连接

## 🛠️ 安装部署

### 1. 克隆项目

```bash
git clone https://github.com/bright-angel/web-monitor
cd web-monitor
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 环境配置

复制环境变量模板并配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```bash
# 必需配置
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///monitor.db

# 可选配置
ALLOW_REGISTRATION=true
DINGTALK_WEBHOOK=your-dingtalk-webhook
DINGTALK_SECRET=your-dingtalk-secret
SELF_CHECK_ENABLED=true
SELF_CHECK_CRON=0 * * * *
PLATFORM_NAME=网站监控平台
```

### 4. 初始化数据库

```bash
python app.py
```

### 5. 启动服务

#### 开发模式
```bash
python app.py
```

#### 生产模式
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## 📖 使用指南

### 1. 用户注册/登录

- 访问 `/register` 进行用户注册
- 访问 `/login` 进行用户登录
- 支持密码重置功能

### 2. 网站管理

#### 添加网站
1. 登录后访问 "网站列表"
2. 点击 "添加网站"
3. 填写网站信息：
   - 网站名称：便于识别的名称
   - 网站URL：完整的HTTP/HTTPS地址
   - 调度类型：间隔时间 或 Cron表达式
   - 检查间隔：间隔模式下的时间间隔(秒)
   - Cron表达式：Cron模式下的表达式
   - 超时时间：请求超时时间(秒)
   - 期望状态码：期望的HTTP状态码
   - 通知渠道：选择接收通知的渠道

#### 网站操作
- **编辑**: 修改网站配置
- **删除**: 删除网站监控
- **立即检查**: 手动触发网站状态检查
- **查看日志**: 查看监控历史记录

### 3. 通知渠道管理

#### 钉钉通知配置
1. 在钉钉群中添加"自定义"机器人
2. 获取Webhook地址和密钥
3. 在平台中添加通知渠道：
   - 渠道名称：自定义名称
   - 渠道类型：钉钉
   - Webhook URL：钉钉机器人Webhook地址
   - 密钥：钉钉机器人密钥（可选）
   - 启用状态：是否启用

#### 测试通知
- 添加渠道后可点击"测试"按钮验证配置

### 4. 监控配置示例

#### 每5分钟检查一次
- 调度类型：间隔时间
- 检查间隔：300

#### 每天9点检查
- 调度类型：Cron表达式
- Cron表达式：0 9 * * *

#### 工作日每2小时检查
- 调度类型：Cron表达式
- Cron表达式：0 */2 * * 1-5

## 🔧 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 | 必需 |
|--------|------|--------|------|
| SECRET_KEY | Flask密钥 | dev-secret-key-change-me | 是 |
| DATABASE_URL | 数据库连接字符串 | sqlite:///monitor.db | 否 |
| ALLOW_REGISTRATION | 是否允许注册 | true | 否 |
| DINGTALK_WEBHOOK | 钉钉Webhook | - | 否 |
| DINGTALK_SECRET | 钉钉密钥 | - | 否 |
| SELF_CHECK_ENABLED | 启用平台自查 | true | 否 |
| SELF_CHECK_CRON | 平台自查Cron | 0 * * * * | 否 |
| PLATFORM_NAME | 平台名称 | 网站监控平台 | 否 |

### Cron表达式说明

Cron表达式格式：`秒 分 时 日 月 星期`

| 字段 | 范围 | 允许的特殊字符 |
|------|------|---------------|
| 秒 | 0-59 | , - * / |
| 分 | 0-59 | , - * / |
| 时 | 0-23 | , - * / |
| 日 | 1-31 | , - * ? / L W |
| 月 | 1-12 | , - * / |
| 星期 | 0-7 | , - * ? / L # |

#### 常用Cron表达式

- `0 * * * *` - 每小时整点
- `0 */6 * * *` - 每6小时
- `0 9 * * *` - 每天9点
- `0 9,15,21 * * *` - 每天9点、15点、21点
- `0 */2 * * 1-5` - 工作日每2小时
- `0 0 * * 0` - 每周日凌晨

## 🏥 健康检查

平台提供多个健康检查接口：

### 完整健康检查
```
GET /health
```
返回详细的系统状态信息，包括数据库连接、系统资源使用情况等。

### 存活探针
```
GET /health/live
```
用于Kubernetes/Docker存活检查。

### 就绪探针
```
GET /health/ready
```
用于Kubernetes/Docker就绪检查。

## 🔍 API接口

### 认证相关
- `POST /login` - 用户登录
- `POST /register` - 用户注册
- `GET /logout` - 用户登出

### 网站管理
- `GET /websites` - 获取网站列表
- `POST /websites/add` - 添加网站
- `GET /websites/<id>/edit` - 获取编辑表单
- `POST /websites/<id>/edit` - 更新网站
- `POST /websites/<id>/delete` - 删除网站
- `POST /websites/<id>/check` - 立即检查网站
- `GET /websites/<id>/logs` - 获取监控日志

### 通知渠道
- `GET /channels` - 获取渠道列表
- `POST /channels/add` - 添加渠道
- `GET /channels/<id>/edit` - 获取编辑表单
- `POST /channels/<id>/edit` - 更新渠道
- `POST /channels/<id>/delete` - 删除渠道
- `POST /channels/<id>/test` - 测试渠道

### 数据接口
- `GET /api/websites/status` - 获取网站状态统计

## 🐳 Docker部署

### 构建镜像
```bash
docker build -t web-monitor .
```

### 运行容器
```bash
docker run -d \
  --name web-monitor \
  -p 5000:5000 \
  -v ./data:/app/data \
  -e SECRET_KEY=your-secret-key \
  -e DATABASE_URL=sqlite:///data/monitor.db \
  web-monitor
```

### Docker Compose
```yaml
version: '3.8'
services:
  web-monitor:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./data:/app/data
    environment:
      - SECRET_KEY=your-secret-key
      - DATABASE_URL=sqlite:///data/monitor.db
      - ALLOW_REGISTRATION=true
    restart: unless-stopped
```

## 🔧 故障排除

### 常见问题

#### 1. 数据库连接错误
- 检查 `DATABASE_URL` 配置
- 确保数据库服务正常运行
- 检查文件权限

#### 2. 定时任务不执行
- 检查APScheduler日志
- 确认Cron表达式格式正确
- 验证网站配置信息

#### 3. 通知发送失败
- 验证Webhook URL有效性
- 检查网络连接
- 确认渠道配置正确

#### 4. 监控状态异常
- 检查目标网站可访问性
- 验证SSL证书有效性
- 确认防火墙配置

### 日志查看

应用日志会输出到控制台，生产环境建议配置日志收集：

```bash
# 查看应用日志
docker logs web-monitor

# 实时查看日志
docker logs -f web-monitor
```

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🆘 技术支持

如有问题或建议，请：

1. 查看本文档的故障排除部分
2. 搜索已有的 Issues
3. 创建新的 Issue 描述问题

## 🔄 更新日志

### v1.0.0
- 初始版本发布
- 基础网站监控功能
- 用户认证系统
- 钉钉通知支持
- 健康检查接口

---

**网站监控平台** - 让网站监控变得简单高效！