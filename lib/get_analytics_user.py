from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunRealtimeReportRequest
from google.oauth2 import service_account
import sys
import os
import requests
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.logger import app_logger as logger


def get_active_users(KEY_FILE_LOCATION, PROPERTY_ID):
    # 初始化凭证
    credentials = service_account.Credentials.from_service_account_file(
        KEY_FILE_LOCATION,
        scopes=['https://www.googleapis.com/auth/analytics.readonly']
    )

    # 创建客户端
    # logger.info("analytics -- 创建客户端连接")
    client = BetaAnalyticsDataClient(credentials=credentials)

    # 创建报告请求
    request = RunRealtimeReportRequest(
        property=PROPERTY_ID,
        metrics=[{"name": "activeUsers"}]
    )

    # 获取报告
    response = client.run_realtime_report(request)

    # 解析结果
    active_users = 0
    if response.row_count > 0:
        active_users = int(response.rows[0].metric_values[0].value)
        logger.info(f"analytics -- 当前在线人数:{active_users}")

    return active_users



def get_mock_users(api_url):
    """
    通过HTTP请求获取模拟在线人数
    
    参数:
        api_url (str): API接口地址
        
    返回:
        dict: 包含在线人数和其他信息的字典
        None: 请求失败时返回None
    """
    try:
        response = requests.get(api_url, timeout=5)
        response.raise_for_status()  # 如果状态码不是200，抛出异常
        data = response.json()
        return data['online_users']
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return None

if __name__ == "__main__":

    # from conf import settings
    # users = get_active_users(settings.KEY_FILE_LOCATION, settings.PROPERTY_ID)
    # print(f"当前在线用户数: {users}")

    users = get_mock_users(api_url="http://IP:5000/api/online-users")
    print(users)