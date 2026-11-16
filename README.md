# 辽宁医保药品交易 - 订单自动监控推送

每15分钟自动检查辽宁医保公共服务平台的新发货订单，通过 PushPlus 推送到微信。

## 功能

- 🔐 自动登录（含 OCR 验证码识别）
- 📦 自动导航到「药品交易结算 → 发货退货管理 → 单订单发货」
- 📅 利用日期筛选器高效检测新订单
- 📱 通过 PushPlus 推送完整订单信息到微信（10个字段 + 药品明细）
- ⏰ 仅在工作时间（8:00-18:00）运行
- 📝 完善的日志记录和错误告警

## 快速开始

### 1. 部署

```bash
# 一键部署
chmod +x deploy.sh
bash deploy.sh
```

### 2. 配置

编辑 `.env` 文件：

```env
YBJ_USERNAME=你的账号
YBJ_PASSWORD=你的密码
PUSHPLUS_TOKEN=你的PushPlus Token
```

### 3. 测试运行

```bash
source venv/bin/activate

# 1. 发送一条测试微信通知（验证 PushPlus）
python main.py --test-notify
# 或者直接使用快捷管理脚本：
./service.sh test

# 2. 单次运行订单检查（抓取医保平台并检测）
python main.py --once
# 或者：
./service.sh once
```

### 4. 服务管理（支持两种模式）

#### 方式 A：使用 systemd 服务（推荐系统主机环境）

```bash
# 复制服务文件并启用开机自启
sudo cp systemd/order-checker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now order-checker

# 查看状态与日志
sudo systemctl status order-checker
sudo journalctl -u order-checker -f
```

#### 方式 B：使用内置守护脚本 service.sh（容器或通用环境）

```bash
./service.sh start    # 启动后台监控守护进程
./service.sh status   # 查看服务运行状态及近期日志
./service.sh stop     # 停止后台服务
./service.sh restart  # 重启后台服务
./service.sh test        # 调试发送一条系统测试微信通知
./service.sh test-order  # 调试发送一条模拟订单卡片到微信
./service.sh once        # 手动立即触发一次订单抓取（忽略工作时间限制）
```

## 项目结构

```
wife_work/
├── .env                  # 配置文件（凭据、Token）
├── .env.example          # 配置模板
├── config.py             # 配置加载
├── main.py               # 程序入口 + 定时调度
├── browser_automation.py # Playwright 浏览器自动化
├── captcha_solver.py     # 验证码 OCR
├── order_checker.py      # 订单增量检测
├── notifier.py           # PushPlus 微信推送
├── deploy.sh             # 部署脚本
├── requirements.txt      # Python 依赖
├── systemd/              # systemd 服务文件
├── data/                 # 数据文件（自动创建）
└── logs/                 # 日志文件（自动创建）
```

## 配置说明

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `YBJ_USERNAME` | 医保平台账号 | - |
| `YBJ_PASSWORD` | 医保平台密码 | - |
| `PUSHPLUS_TOKEN` | PushPlus 用户 Token | - |
| `PUSHPLUS_TO` | PushPlus 好友令牌（可选，指定接收好友） | - |
| `CHECK_INTERVAL` | 检查间隔（分钟） | 15 |
| `WORK_HOUR_START` | 工作开始时间 | 8 |
| `WORK_HOUR_END` | 工作结束时间 | 18 |
| `CAPTCHA_MAX_RETRIES` | 验证码最大重试次数 | 5 |
| `HEADLESS` | 无头模式 | true |

## 故障排查

- **验证码识别失败**: 查看 `logs/login_page_debug.png` 截图
- **登录失败**: 查看 `logs/login_failed.png` 截图
- **运行异常**: 查看 `logs/error_screenshot.png` 截图
- **日志文件**: `logs/app.log`
