
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
services:
  frigate:
    container_name: frigate
    privileged: true
    restart: unless-stopped
    stop_grace_period: 30s                  # 为各服务提供足够的关闭时间
    image: ghcr.io/workerspages/frigate-mosquitto-bark:latest
    shm_size: "128mb"                      # 分配共享内存，跑一两个摄像头 128M 足够了
    volumes:
      - /etc/localtime:/etc/localtime:ro   # 同步宿主机时间
      - ./config:/config                   # 映射刚刚写的配置文件
      - ./frigate:/media/frigate           # 映射录像和抓拍的保存路径
      - type: tmpfs                        # 使用内存盘做缓存，拯救硬盘 I/O
        target: /tmp/cache
        tmpfs:
          size: 1000000000                  # 分配 1G 内存给实时缓存
    ports:
      - "8971:8971"       # Frigate Web 管理界面端口
      - "8554:8554"       # RTSP 转发端口 (可选)
      - "8555:8555/tcp"   # WebRTC 视频流端口 (可选，低延迟看直播用)
      - "8555:8555/udp"   # WebRTC 视频流端口 (可选)
      - "5000:5000"       # 暴露 5000 这个“免密验证”端口，让 Bark App 能顺利把图片拉取下来 (不将任何端口暴露到公网)
    environment:
      - TZ=Asia/Shanghai                               # 设置为中国+8时区
      - BARK_URL=https://api.day.app/YOUR_BARK_KEY     # 【必填】你的专属 Bark 推送地址和 Key 
      - FRIGATE_URL=http://192.168.31.100:5000         # 【可选】填入你机器的局域网或公网 IP 地址，让推送能带上抓拍图片
      # - FRIGATE_RTSP_PASSWORD=password               # rtsp的密码，请修改为你期望的密码
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
---

使用 **Cloudflare Tunnels（内网穿透）** 是目前业界公认最优雅、最安全的无公网 IP 远程访问方案。它不需要在路由器上开放任何端口，自带 HTTPS 加密，而且完全隐藏了你家里的真实公网 IP。

既然你已经有了这个强大的基础设施，我们就可以非常清晰地规划你的配置了。

不过，在使用 Cloudflare Tunnels 配合 Bark 时，我们会遇到一个经典的“安全与便利的博弈”。以下是为你梳理的利弊和最佳实践：

### ⚠️ 核心矛盾：Bark 需要“敞开的门”

如果你通过 Cloudflare Tunnels 绑定了一个域名（比如 `frigate.你的域名.com`）直接映射到 Frigate 的 **5000** 端口，并在环境变量中填入 `FRIGATE_URL="https://frigate.你的域名.com"`：

* **爽点**：你的手机无论在世界哪个角落，只要有网，Bark 收到推送就能秒开出抓拍图片。
* **致命风险**：由于 5000 端口没有密码验证，这意味着你把家里毫无防御的监控 API 暴露在了整个互联网上。

> *(补充知识：有些人以为随便起一个很长很生僻的子域名（比如 `a1b2c3d4.你的域名.com`）别人就猜不到。这在现代互联网是行不通的，因为有 **证书透明度日志 (CT Logs)** 的存在，你刚在 Cloudflare 解析好域名，全世界的爬虫立刻就能拿到这个网址并尝试访问。)*

---

### 🛡️ 最佳配置方案（强烈建议）

鉴于你已经有了 Cloudflare Tunnels，我强烈推荐你采用“域名走 8971 保安全，Bark 走纯文本做提醒”的架构。

**1. Cloudflare Tunnels 端配置：**
在你的 Cloudflare 后台，新建一个 Public Hostname，将其映射到 Frigate 容器的 **8971 端口**（例如：`http://192.168.31.100:8971`）。

* 这样你在外面时，随时可以通过 `https://frigate.你的域名.com` 安全地访问 Frigate 的完整后台查看录像，且有密码保护。

**2. docker-compose.yml 端修改：**
将 `FRIGATE_URL` 留空或者直接删除这一行，保留 5000 端口供本地内部使用。

```yaml
    environment:
      - TZ=Asia/Shanghai
      - BARK_URL=https://api.day.app/YOUR_BARK_KEY
      # - FRIGATE_URL=""  # 留空或删除，放弃外部拉取图片

```

**3. 最终体验：**

* 当家里有情况时，Bark 会立刻弹窗：`【Frigate 监控警报】摄像头 [大门] 检测到 [人]。`
* 虽然没有附带图片，但你只需点开通知，或者直接在浏览器输入你的 Cloudflare 域名，登录 8971 端口的 Web 界面，就能立刻查看高清晰度的抓拍和事件录像。

---

由于你已经有了极佳的外网访问环境（Cloudflare），这种“纯文字强提醒 + 随时随地安全登录看回放”的组合，是绝大多数 NAS 玩家最终采用的最省心、最稳妥的方案。

你觉得这种“Bark 纯文字提醒 + Cloudflare 域名看录像”的体验符合你的日常使用习惯吗？还是说你对“通知弹窗里必须带图片”有刚性需求（如果有，我们可以探讨接入企业微信或 Telegram 机器人的终极方案）？
