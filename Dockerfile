# 基于 Frigate 官方稳定版镜像
FROM ghcr.io/blakeblackshear/frigate:stable

# 1. 安装 Mosquitto 和 Python 依赖
# 使用 --break-system-packages 是因为新版 Debian 限制了全局 pip 安装，但在容器内这是安全的
RUN apt-get update && \
    apt-get install -y --no-install-recommends mosquitto python3-pip && \
    pip3 install --no-cache-dir paho-mqtt requests --break-system-packages && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 2. 配置 Mosquitto 允许本地匿名连接
RUN echo "listener 1883 127.0.0.1\nallow_anonymous true" > /etc/mosquitto/mosquitto.conf

# 3. 将 Mosquitto 注册为 s6-overlay 服务
RUN mkdir -p /etc/s6-overlay/s6-rc.d/mosquitto && \
    echo "longrun" > /etc/s6-overlay/s6-rc.d/mosquitto/type && \
    echo "#!/command/with-contenv bash\nexec mosquitto -c /etc/mosquitto/mosquitto.conf" > /etc/s6-overlay/s6-rc.d/mosquitto/run && \
    chmod +x /etc/s6-overlay/s6-rc.d/mosquitto/run && \
    mkdir -p /etc/s6-overlay/s6-rc.d/user/contents.d && \
    touch /etc/s6-overlay/s6-rc.d/user/contents.d/mosquitto

# 4. 将 Bark 脚本注册为 s6-overlay 服务
RUN mkdir -p /etc/s6-overlay/s6-rc.d/bark-notifier && \
    echo "longrun" > /etc/s6-overlay/s6-rc.d/bark-notifier/type && \
    echo "#!/command/with-contenv bash\nexec python3 -u /opt/bark/notifier.py" > /etc/s6-overlay/s6-rc.d/bark-notifier/run && \
    chmod +x /etc/s6-overlay/s6-rc.d/bark-notifier/run && \
    touch /etc/s6-overlay/s6-rc.d/user/contents.d/bark-notifier

# 5. 将你的脚本复制到镜像内部一个安全的独立目录中 (避免与你外部映射的 /config 冲突)
RUN mkdir -p /opt/bark
COPY notifier.py /opt/bark/notifier.py
