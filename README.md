
# Frigate Bark Notifier (单容器集成版)

这是一个基于 Frigate 官方镜像深度定制的监控与通知集成方案。它通过底层的 `s6-overlay` 进程管理，在官方 Frigate 容器内部无缝集成了本地 Mosquitto MQTT 代理和 Python 监听推送脚本。

只需部署这一个容器，即可同时实现**实时目标检测**与**手机 Bark 消息自动推送**功能，极大简化了家庭主机的资源占用与网络配置。

## ✨ 核心特性

*   📦 **单容器部署**：无需额外维护独立的 Mosquitto 和 Node-RED / 自定义 Python 容器。
*   🚀 **即时精准推送**：当 Frigate 检测到人员或物体（`new` 事件）时，立即通过 Bark 发送通知。
*   📸 **支持抓拍预览**：在 Bark 推送消息中自动附带事件的缩略图（需配置外部可访问地址）。
*   🔄 **多架构支持**：通过 GitHub Actions 自动构建，支持 `amd64`（X86 电脑/NAS）和 `arm64`（树莓派/ARM 软路由）平台。
*   ☁️ **双镜像仓库**：镜像已自动同步至 Docker Hub 和 GitHub Container Registry (GHCR)。

---

## 🚀 快速开始

### 1. 准备 Frigate 配置文件
在部署之前，你必须准备好 Frigate 的 `config.yml` 配置文件。
**重要提示**：因为 Mosquitto 代理已经集成在当前容器内部，所以你必须在 `config.yml` 中将 MQTT 服务器指向 `127.0.0.1`：

```yaml
mqtt:
  host: 127.0.0.1
  port: 1883
  # 由于开启了匿名访问，无需填写账号密码

cameras:
  # 在此处继续填写你的摄像头配置...

```

### 2. 使用 Docker Compose 部署

你可以直接拉取我们构建好的镜像（请将 `<YOUR_DOCKERHUB_USERNAME>` 替换为你实际的用户名，或者使用 `ghcr.io` 的地址）。创建一个 `docker-compose.yml` 文件：

```yaml
version: '3.9'

services:
  frigate:
    image: ghcr.io/workerspages/frigate-mosquitto-bark:latest
    container_name: frigate
    privileged: true
    restart: unless-stopped
    shm_size: "64mb"
    volumes:
      - /etc/localtime:/etc/localtime:ro
      - ./config:/config
      - ./storage:/media/frigate
      - type: tmpfs
        target: /tmp/cache
        tmpfs:
          size: 1000000000
    ports:
      - "8971:8971"
      - "5000:5000"
    environment:
      # 【必填】你的专属 Bark 推送地址和 Key
      - BARK_URL=[https://api.day.app/YOUR_BARK_KEY](https://api.day.app/YOUR_BARK_KEY)
      # 【可选】填入你机器的局域网或公网 IP 地址，让推送能带上抓拍图片
      - FRIGATE_URL=[http://192.168.1.100:5000](http://192.168.1.100:5000) 

```

运行以下命令启动服务：

```bash
docker-compose up -d

```

---

## ⚙️ 环境变量说明

在启动容器时，可以通过以下环境变量控制通知行为：

| 环境变量名 | 是否必填 | 示例 | 描述 |
| --- | --- | --- | --- |
| `BARK_URL` | **必填** | `https://api.day.app/xxx` | 你的 Bark 服务器地址及推送 Key。如果使用自建服务器，请填写完整域名及 Key。 |
| `FRIGATE_URL` | 选填 | `http://192.168.1.100:5000` | 用于拼接快照图片的 URL 基础路径。**注意：** 你的手机必须能够访问此 URL（无论是在同一个局域网还是通过内网穿透的公网地址），才能在通知中加载出图片。如果不填，则仅推送纯文字报警。 |

---

## 🛠 本地源码构建

如果你希望自己在本地从头构建这个镜像，而不是拉取云端的预编译版本：

1. 克隆本仓库到本地。
2. 确保目录中包含 `Dockerfile`, `notifier.py` 以及配置文件夹。
3. 将你的 `docker-compose.yml` 中的 `image:` 替换为 `build: .`。
4. 执行本地构建并启动命令：

```bash
docker-compose up -d --build

```

---

## 📝 故障排查

如果你没有收到通知，可以通过查看容器日志来定位问题。容器内部运行着 Frigate、Mosquitto 和 Python 脚本。

查看整体日志：

```bash
docker logs -f frigate

```

查看 Python 推送脚本是否成功连接到内部的 MQTT Broker，请在日志中寻找如下字样：

> `成功连接到本机 MQTT Broker: 127.0.0.1:1883`
> `已订阅主题: frigate/events`

当触发报警时，脚本会输出类似如下的日志：

> `成功发送 Bark 通知: Frigate 监控警报 - 摄像头 [front_door] 检测到 [person]。`

```

```
