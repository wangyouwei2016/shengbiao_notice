# 迁移部署指南 (新服务器使用)

本项目为 **辽宁医保药品交易订单定时监控与微信推送服务**。

---

## 快速安装与启动（3 步完成）

### 第一步：解压
```bash
# 解压到当前目录
tar -zxvf wife_work_migrate.tar.gz
cd wife_work
```

### 第二步：一键初始化安装环境
确保新服务器已安装 Python 3.8+（推荐 Python 3.10 或 3.11）及 git/curl。
执行自带的部署脚本（会自动创建 venv、安装依赖及 Playwright 浏览器内核、自动配置服务）：
```bash
bash deploy.sh
```
> 如果系统缺少基础组件，在 Debian/Ubuntu 下可先运行：
> `sudo apt update && sudo apt install -y python3 python3-venv python3-pip`

### 第三步：验证并启动服务

1. **测试微信通知通道**：
   ```bash
   ./service.sh test
   ```
   检查微信是否收到 PushPlus 的测试消息。

2. **测试医保平台抓取**（验证新服务器与医保平台网络连通性）：
   ```bash
   ./service.sh once
   ```
   如果新服务器在国内网络环境下，将能正常秒级打开登录页面并执行检查。

3. **启动后台常驻运行**：
   ```bash
   ./service.sh start
   ```
   或者使用 systemd 守护进程（支持开机自启、崩溃自启）：
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now order-checker
   ```

---

## 常用运维管理命令

```bash
./service.sh status     # 查看当前运行状态及最新日志
./service.sh stop       # 停止后台监控
./service.sh restart    # 重启服务
./service.sh once       # 立即手动检查一次订单（忽略工作时间限制）
./service.sh test-order # 发送一条模拟订单卡片到微信
tail -f logs/app.log    # 实时查看日志输出
```

---

## 配置文件说明 (`.env`)

所有账号密码与推送配置已随包保留在 `.env` 文件中：
- `YBJ_USERNAME`：医保平台登录用户名
- `YBJ_PASSWORD`：医保平台密码
- `PUSHPLUS_TOKEN`：PushPlus 微信推送 Token
- `PUSHPLUS_TO`：PushPlus 一对多推送群组/好友编码（可选）
- `WORK_HOUR_START` / `WORK_HOUR_END`：工作时间范围（默认 8 点至 18 点）
- `CHECK_INTERVAL`：检查频率（默认每 15 分钟）
- `HEADLESS`：是否使用无头浏览器（默认 `true`）
