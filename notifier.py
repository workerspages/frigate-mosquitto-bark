import paho.mqtt.client as mqtt
import requests
import json
import os
import sys

# 因为在同一个容器内，直连 localhost
MQTT_BROKER = "127.0.0.1" 
MQTT_PORT = 1883
MQTT_TOPIC = "frigate/events"
BARK_URL = os.getenv("BARK_URL")
FRIGATE_URL = os.getenv("FRIGATE_URL", "")

if not BARK_URL:
    print("错误: 请在环境变量中设置 BARK_URL (例如: https://api.day.app/YOUR_KEY)。")
    sys.exit(1)

def send_bark_notification(title, body, image_url=None):
    payload = {
        "title": title,
        "body": body,
        "group": "Frigate"
    }
    
    if image_url:
        payload["icon"] = image_url

    try:
        clean_url = BARK_URL.rstrip('/')
        response = requests.post(clean_url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"成功发送 Bark 通知: {title} - {body}")
        else:
            print(f"发送 Bark 通知失败, 状态码: {response.status_code}, 响应: {response.text}")
    except Exception as e:
        print(f"请求 Bark 服务发生异常: {e}")

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"成功连接到本机 MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(MQTT_TOPIC)
        print(f"已订阅主题: {MQTT_TOPIC}")
    else:
        print(f"连接 MQTT Broker 失败, 返回码: {rc}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        event_type = payload.get("type")
        after = payload.get("after", {})

        if event_type == "new":
            camera = after.get("camera", "未知摄像头")
            label = after.get("label", "未知物体")
            event_id = after.get("id", "")
            
            title = "Frigate 监控警报"
            body = f"摄像头 [{camera}] 检测到 [{label}]。"
            
            image_url = None
            if FRIGATE_URL and event_id:
                image_url = f"{FRIGATE_URL.rstrip('/')}/api/events/{event_id}/snapshot.jpg"

            send_bark_notification(title, body, image_url)
            
    except json.JSONDecodeError:
        pass
    except Exception as e:
        print(f"处理 MQTT 消息发生异常: {e}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

print("正在启动 Frigate Bark 通知服务...")
try:
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()
except Exception as e:
    print(f"启动 MQTT 客户端失败: {e}")
    sys.exit(1)
