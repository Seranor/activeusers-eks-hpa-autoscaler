from flask import Flask, jsonify, request
import time
import logging
import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 基础配置
INITIAL_USERS = 6
GROWTH_RATE = 3
PAUSE_THRESHOLDS = [500,600,1000, 2000, 3000, 4000]  # 需要暂停的人数节点

# 状态变量
start_time = time.time()
start_datetime = datetime.datetime.now()
paused = False
pause_time = None
accumulated_time = 0  # 累计已经暂停的时间
current_threshold_index = 0  # 当前处理的阈值索引

def calculate_online_users():
    global paused, pause_time, accumulated_time, current_threshold_index
    
    # 计算实际流逝的时间（减去暂停的时间）
    if paused:
        effective_elapsed_seconds = pause_time - start_time - accumulated_time
    else:
        effective_elapsed_seconds = time.time() - start_time - accumulated_time
    
    # 计算当前理论上的用户数
    additional_users = int(effective_elapsed_seconds * GROWTH_RATE)
    current_users = INITIAL_USERS + additional_users
    
    # 检查是否需要暂停
    if (not paused and 
        current_threshold_index < len(PAUSE_THRESHOLDS) and 
        current_users >= PAUSE_THRESHOLDS[current_threshold_index]):
        paused = True
        pause_time = time.time()
        logger.info(f"已达到 {PAUSE_THRESHOLDS[current_threshold_index]} 人，增长已暂停")
    
    # 如果已暂停，返回暂停时的人数
    if paused:
        return PAUSE_THRESHOLDS[current_threshold_index]
    
    return current_users

@app.route('/api/online-users', methods=['GET'])
def get_online_users():
    current_users = calculate_online_users()
    current_time = datetime.datetime.now()
    
    response = {
        'online_users': current_users,
        'start_time': start_datetime.isoformat(),
        'current_time': current_time.isoformat(),
        'elapsed_seconds': int(time.time() - start_time - accumulated_time),
        'growth_rate': f"{GROWTH_RATE}",
        'paused': paused
    }
    
    # 如果处于暂停状态，添加额外信息
    if paused:
        response['paused_at'] = PAUSE_THRESHOLDS[current_threshold_index]
        response['pause_duration'] = int(time.time() - pause_time) if pause_time else 0
    
    return jsonify(response)

@app.route('/api/continue-growth', methods=['POST'])
def continue_growth():
    """继续增长的API端点"""
    global paused, accumulated_time, current_threshold_index
    
    if not paused:
        return jsonify({
            'status': 'error',
            'message': '当前未处于暂停状态'
        }), 400
    
    # 计算已暂停的时间并累加
    pause_duration = time.time() - pause_time
    accumulated_time += pause_duration
    
    # 更新状态
    paused = False
    current_threshold_index += 1
    
    logger.info(f"继续增长，已在 {PAUSE_THRESHOLDS[current_threshold_index-1]} 人处暂停了 {int(pause_duration)} 秒")
    
    return jsonify({
        'status': 'success',
        'message': f'增长已继续，已在 {PAUSE_THRESHOLDS[current_threshold_index-1]} 人处暂停了 {int(pause_duration)} 秒',
        'next_pause': PAUSE_THRESHOLDS[current_threshold_index] if current_threshold_index < len(PAUSE_THRESHOLDS) else None
    })

@app.route('/api/reset', methods=['POST'])
def reset_simulation():
    """重置模拟器"""
    global start_time, start_datetime, paused, pause_time, accumulated_time, current_threshold_index
    
    start_time = time.time()
    start_datetime = datetime.datetime.now()
    paused = False
    pause_time = None
    accumulated_time = 0
    current_threshold_index = 0
    
    logger.info("模拟器已重置")
    
    return jsonify({
        'status': 'success',
        'message': '模拟器已重置',
        'online_users': INITIAL_USERS
    })

@app.route('/api/status', methods=['GET'])
def get_status():
    """获取当前模拟器状态"""
    current_users = calculate_online_users()
    
    status = {
        'online_users': current_users,
        'paused': paused,
        'initial_users': INITIAL_USERS,
        'growth_rate': GROWTH_RATE,
        'pause_thresholds': PAUSE_THRESHOLDS,
        'elapsed_seconds': int(time.time() - start_time - accumulated_time),
    }
    
    if paused:
        status['current_pause_threshold'] = PAUSE_THRESHOLDS[current_threshold_index]
        status['pause_duration'] = int(time.time() - pause_time) if pause_time else 0
    
    if current_threshold_index < len(PAUSE_THRESHOLDS):
        status['next_pause_threshold'] = PAUSE_THRESHOLDS[current_threshold_index]
    else:
        status['next_pause_threshold'] = None
    
    return jsonify(status)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'service': 'online-users-simulator'})

if __name__ == '__main__':
    port = 5000
    logger.info(f"在线人数模拟服务启动于端口 {port}")
    logger.info(f"初始人数: {INITIAL_USERS}, 增长率: {GROWTH_RATE} 人/秒")
    logger.info(f"将在以下人数节点暂停: {PAUSE_THRESHOLDS}")
    logger.info(f"访问 http://localhost:{port}/api/online-users 获取在线人数")
    logger.info(f"使用 POST 请求 http://localhost:{port}/api/continue-growth 继续增长")
    
    app.run(host='0.0.0.0', port=port, debug=False)
