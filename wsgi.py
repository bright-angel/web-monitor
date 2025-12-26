"""WSGI入口文件 - 用于生产环境部署"""
from app import app, init_db
from monitor import init_scheduler

# 初始化数据库
init_db()

# 初始化调度器
scheduler = init_scheduler(app)

if __name__ == '__main__':
    app.run()
