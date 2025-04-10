import json
import time
import requests
from typing import Dict, Any, List, Optional, Callable
from functools import wraps
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.logger import app_logger as logger


# 重试装饰器
def retry_decorator(max_retries=3, delay=2, backoff_factor=2,
                    exceptions=(Exception,)):
    """
    重试装饰器

    Args:
        max_retries: 最大重试次数
        delay: 初始重试延迟(秒)
        backoff_factor: 退避因子，每次重试延迟时间会乘以这个系数
        exceptions: 需要捕获的异常类型
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None

            for retry_count in range(max_retries + 1):
                try:
                    if retry_count > 0:
                        logger.info(f"feishu bot -- 第 {retry_count} 次重试...")

                    result = func(*args, **kwargs)

                    # 如果是发送消息的函数，检查响应结果
                    if isinstance(result, dict) and ("code" in result or "success" in result):
                        if "code" in result and result.get("code") != 0:
                            if retry_count < max_retries:
                                logger.warning(f"feishu bot -- 请求返回错误码: {result.get('code')}, 准备重试")
                                time.sleep(current_delay)
                                current_delay *= backoff_factor
                                continue

                    # 成功执行，返回结果
                    return result

                except exceptions as e:
                    last_exception = e
                    if retry_count < max_retries:
                        logger.warning(f"feishu bot -- 发生异常: {str(e)}, 准备重试")
                        time.sleep(current_delay)
                        current_delay *= backoff_factor
                    else:
                        logger.error(f"feishu bot -- 重试达到最大次数({max_retries})，放弃重试")

            # 所有重试失败，抛出最后一个异常
            if last_exception:
                raise last_exception

            return None

        return wrapper

    return decorator


class FeishuRichTextBot:
    """飞书机器人富文本通知模块(带重试功能)"""

    def __init__(self, webhook_url: str, secret: Optional[str] = None,
                 max_retries: int = 3, retry_delay: int = 2):
        """
        初始化飞书机器人

        Args:
            webhook_url: 飞书机器人的Webhook地址
            secret: 飞书机器人的签名密钥（如果开启了签名验证，可选）
            max_retries: 最大重试次数
            retry_delay: 重试间隔(秒)
        """
        self.webhook_url = webhook_url
        self.secret = secret
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    @retry_decorator(max_retries=3, delay=2, exceptions=(requests.RequestException, json.JSONDecodeError))
    def send_rich_text(self, title: str, content: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        发送富文本消息(带重试功能)

        Args:
            title: 消息标题
            content: 富文本内容，格式为二维数组，包含各种元素
                    例如：[[{"tag": "text", "text": "内容"}],
                         [{"tag": "a", "text": "链接", "href": "https://example.com"}]]

        Returns:
            服务器响应结果
        """
        message = {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {  # 中文内容
                        "title": title,
                        "content": content
                    }
                }
            }
        }

        # 添加签名（如果提供了secret）
        if self.secret:
            import base64
            import hashlib
            import hmac

            timestamp = str(int(time.time()))
            string_to_sign = f"{timestamp}\n{self.secret}"
            sign = base64.b64encode(
                hmac.new(
                    string_to_sign.encode("utf-8"),
                    digestmod=hashlib.sha256
                ).digest()
            ).decode('utf-8')

            message.update({
                "timestamp": timestamp,
                "sign": sign
            })

        # 发送请求
        headers = {"Content-Type": "application/json"}

        # 此方法本身带有重试机制，由装饰器提供
        response = requests.post(
            self.webhook_url,
            headers=headers,
            data=json.dumps(message),
            timeout=10  # 添加超时设置
        )

        response_json = response.json()

        if response.status_code != 200 or response_json.get("code") != 0:
            logger.error(f"feishu bot -- 消息发送失败: {response_json}")
            # 这里不需要手动重试，装饰器会处理
        else:
            logger.info("feishu bot -- 富文本消息发送成功")

        return response_json


if __name__ == '__main__':
    # 初始化机器人(指定重试参数)
    webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/"
    bot = FeishuRichTextBot(
        webhook_url=webhook_url,
        max_retries=5,  # 最大重试5次
        retry_delay=1  # 初始重试延迟1秒
    )

    # 构建富文本内容
    rich_content = [
        # 第一行
        [
            {"tag": "text", "text": "系统状态："},
            {"tag": "text", "text": "警告", "color": "orange"}
        ],
        # 第二行
        [
            {"tag": "text", "text": "CPU使用率："},
            {"tag": "text", "text": "85%", "color": "red"}
        ],
        [],
        # 第三行
        [
            {"tag": "text", "text": "详细日志："},
            {"tag": "a", "text": "点击查看", "href": "https://example.com/logs"}
        ]
    ]

    # 发送富文本消息(将自动重试)
    try:
        response = bot.send_rich_text("系统监控告警", rich_content)
        print(f"消息发送结果: {response}")
    except Exception as e:
        print(f"最终发送失败: {str(e)}")
