from app import create_app
import sys
import os
from apscheduler.schedulers.background import BackgroundScheduler
from concurrent.futures import ProcessPoolExecutor
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.core import AutoScalingService
from lib.logger import logger
from conf import settings

app = create_app()

def auto_scaling_scheduler():
    """使用BackgroundScheduler启动定时检查任务"""
    auto_scaling = AutoScalingService()
    
    # 正确配置APScheduler
    executors = {
        'default': {'type': 'threadpool', 'max_workers': 1},
        'processpool': {'type': 'processpool', 'max_workers': 1}  # 修正这里
    }
    
    job_defaults = {
        'coalesce': False,
        'max_instances': 1
    }
    
    scheduler = BackgroundScheduler(executors=executors, job_defaults=job_defaults)
    
    # 添加定时任务，每5分钟执行一次
    scheduler.add_job(
        auto_scaling.check_and_scale,
        'interval',
        minutes=settings.CHECK_TIME,
        id='autoscaling_job'
    )
    
    # 立即执行一次
    scheduler.add_job(
        auto_scaling.check_and_scale,
        id='initial_check'
    )
    
    # 启动调度器
    scheduler.start()
    logger.info("自动伸缩服务已启动，每5分钟执行一次检查")
    
    # 注册应用关闭时的清理函数
    import atexit
    atexit.register(lambda: scheduler.shutdown(wait=False))
    atexit.register(lambda: auto_scaling.scaling_manager.close())
    
    return scheduler


if __name__ == '__main__':
    scheduler = auto_scaling_scheduler()
    app.run(debug=False, host='0.0.0.0', port=6000)
