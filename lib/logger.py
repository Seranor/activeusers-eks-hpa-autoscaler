from loguru import logger
import sys
import os
from datetime import datetime
import inspect


def setup_logger():
    """配置并返回 logger 实例"""
    # 创建日志目录
    current_file = os.path.abspath(inspect.getfile(inspect.currentframe()))
    utils_dir = os.path.dirname(current_file)
    project_root = os.path.dirname(utils_dir)  # 向上两级
    log_dir = os.path.join(project_root, "logs")
    # log_dir = "logs"

    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 移除默认处理器
    logger.remove()

    # 输出格式
    log_format = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}"

    # 控制台输出
    logger.add(
        sys.stderr,
        format=log_format,
        level="INFO",
        colorize=True
    )

    # 文件输出，按日期轮转
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(log_dir, f"app_{today}.log")
    logger.add(
        log_file,
        format=log_format,
        level="DEBUG",
        rotation="00:00",  # 每天午夜轮转
        retention="7 days",  # 保留30天
        compression="zip",  # 压缩旧日志
        enqueue=True,  # 多进程安全
        encoding="utf-8"  # 中文支持
    )

    # 错误日志单独存储
    error_log = os.path.join(log_dir, f"error_{today}.log")
    logger.add(
        error_log,
        format=log_format,
        level="ERROR",
        rotation="00:00",
        retention="30 days",
        compression="zip",
        enqueue=True,
        encoding="utf-8"
    )

    return logger


# 获取配置好的 logger
app_logger = setup_logger()
