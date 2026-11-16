#!/bin/bash
set -e

echo "=== 辽宁医保订单监控 - 部署脚本 ==="
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 需要 Python 3.8+"
    exit 1
fi
echo "✅ Python: $(python3 --version)"

# 创建虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
fi
source venv/bin/activate

# 安装依赖
echo "📦 安装 Python 依赖..."
pip install -r requirements.txt

# 安装 Playwright Chromium
echo "🌐 安装 Chromium 浏览器..."
playwright install chromium
echo "🌐 安装系统依赖（可能需要 sudo）..."
playwright install-deps || echo "⚠️  install-deps 失败，可能需要 sudo 权限"

# 复制并根据当前目录配置服务文件
CURRENT_DIR="$(pwd)"
if [ -d "/etc/systemd/system" ]; then
    echo "⚙️ 配置 systemd 服务 (安装目录: $CURRENT_DIR)..."
    sed -e "s|/root/wife-shengbiao-notice/wife_work|$CURRENT_DIR|g" systemd/order-checker.service > /tmp/order-checker.service
    cp /tmp/order-checker.service /etc/systemd/system/order-checker.service 2>/dev/null && systemctl daemon-reload 2>/dev/null || echo "⚠️ 拷贝 service 文件需 root 权限"
    rm -f /tmp/order-checker.service
fi

# 创建 .env（如果不存在）
if [ ! -f .env ]; then
    cp .env.example .env
    chmod 600 .env
    echo ""
    echo "⚠️  请编辑 .env 文件填写凭据和 Token"
fi

echo ""
echo "============================================"
echo "✅ 部署完成！"
echo ""
echo "📋 使用方法:"
echo "   1. 编辑 .env 配置文件"
echo "   2. 测试运行（有头模式）:"
echo "      source venv/bin/activate"
echo "      HEADLESS=false python main.py --once"
echo "   3. 启动定时任务:"
echo "      source venv/bin/activate"
echo "      python main.py"
echo ""
echo "📋 部署为系统服务:"
echo "   sudo cp systemd/order-checker.service /etc/systemd/system/"
echo "   sudo systemctl enable --now order-checker"
echo "   sudo journalctl -u order-checker -f"
echo "============================================"
