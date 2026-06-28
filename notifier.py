import paho.mqtt.client as mqtt
import requests
import json
import os
import sys
import logging

# ==========================================
# 1. 设置标准化日志记录 (适用于 Docker 容器日志)
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# ==========================================
# 2. 环境变量与全局配置读取
# ==========================================
# 因为在同一个容器内，直连 localhost
MQTT_BROKER = "127.0.0.1" 
MQTT_PORT = 1883
MQTT_TOPIC = "frigate/events"
BARK_URL = os.getenv("BARK_URL")
FRIGATE_URL = os.getenv("FRIGATE_URL", "")

if not BARK_URL:
    logging.error("错误: 请在环境变量中设置 BARK_URL (例如: https://api.day.app/YOUR_KEY)。")
    sys.exit(1)

# ==========================================
# 3. Bark 推送核心逻辑
# ==========================================
def send_bark_notification(title, body, image_url=None, click_url=None):
    payload = {
        "title": title,
        "body": body,
        "group": "Frigate",
        "level": "timeSensitive"  # 开启强提醒，可穿透 iOS 专注模式
    }
    
    if image_url:
        payload["icon"] = image_url
        
    if click_url:
        payload["url"] = click_url # 点击通知栏直接跳转到浏览器

    try:
        clean_url = BARK_URL.rstrip('/')
        # 设置 timeout 防止网络拥塞导致进程阻塞
        response = requests.post(clean_url, json=payload, timeout=10)
        
        if response.status_code == 200:
            logging.info(f"成功发送 Bark 通知: [{title}] {body}")
        else:
            logging.error(f"发送 Bark 通知失败, 状态码: {response.status_code}, 响应: {response.text}")
    except Exception as e:
        logging.error(f"请求 Bark 服务发生异常: {e}")

# ==========================================
# 4. MQTT 回调函数
# ==========================================
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logging.info(f"成功连接到本机 MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(MQTT_TOPIC)
        logging.info(f"已订阅主题: {MQTT_TOPIC}")
    else:
        logging.error(f"连接 MQTT Broker 失败, 返回码: {rc}")

def on_disconnect(client, userdata, rc):
    if rc != 0:
        logging.warning(f"意外断开 MQTT Broker 连接 (返回码: {rc})，正在尝试重连...")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        event_type = payload.get("type")
        after = payload.get("after", {})

        # 只处理新产生的事件 (new)
        if event_type == "new":
            camera = after.get("camera", "未知摄像头")
            label = after.get("label", "未知物体")
            event_id = after.get("id", "")
            
            title = "Frigate 监控警报"
            body = f"摄像头 [{camera}] 检测到 [{label}]。"
            
            image_url = None
            click_url = None
            
            # 如果配置了外部访问的 URL，则拼接图片和跳转链接
            if FRIGATE_URL and event_id:
                base_url = FRIGATE_URL.rstrip('/')
                image_url = f"{base_url}/api/events/{event_id}/snapshot.jpg"
                click_url = f"{base_url}/events"  # 跳转到 Frigate 的事件大厅页面

            send_bark_notification(title, body, image_url, click_url)
            
    except json.JSONDecodeError:
        # 忽略非 JSON 格式的消息
        pass
    except Exception as e:
        logging.error(f"处理 MQTT 消息发生异常: {e}")

# ==========================================
# 5. 主程序启动逻辑
# ==========================================
client = mqtt.Client()
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message

logging.info("正在启动 Frigate Bark 通知服务...")
try:
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    # loop_forever 内部自带断线自动重连机制
    client.loop_forever()
except Exception as e:
    logging.error(f"启动 MQTT 客户端失败: {e}")
    sys.exit(1)
