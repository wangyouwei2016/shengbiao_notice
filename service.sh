#!/usr/bin/env bash
# ==========================================================
# 辽宁医保药品交易订单监控 - Linux 服务管理脚本
# ==========================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PID_FILE="$SCRIPT_DIR/data/order-checker.pid"
LOG_FILE="$SCRIPT_DIR/logs/app.log"
PYTHON_BIN="$SCRIPT_DIR/venv/bin/python"

mkdir -p "$SCRIPT_DIR/data" "$SCRIPT_DIR/logs"

get_pid() {
    # 优先检查 systemd 服务状态
    if command -v systemctl &>/dev/null && systemctl is-active --quiet order-checker 2>/dev/null; then
        local sys_pid
        sys_pid=$(systemctl show -p MainPID --value order-checker 2>/dev/null)
        if [ -n "$sys_pid" ] && [ "$sys_pid" -ne 0 ]; then
            echo "$sys_pid"
            return 0
        fi
    fi

    if [ -f "$PID_FILE" ]; then
        local pid
        pid=$(cat "$PID_FILE")
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            echo "$pid"
            return 0
        fi
    fi
    # 备用方案：通过进程名检查
    local process_pid
    process_pid=$(pgrep -f "$PYTHON_BIN main.py" | head -n 1)
    if [ -n "$process_pid" ]; then
        echo "$process_pid"
        return 0
    fi
    return 1
}

start() {
    local pid
    pid=$(get_pid)
    if [ -n "$pid" ]; then
        echo "⚠️  服务已在运行中 (PID: $pid)"
        return 0
    fi

    if command -v systemctl &>/dev/null && [ -f "/etc/systemd/system/order-checker.service" ] && systemctl status &>/dev/null; then
        echo "🚀 正在通过 systemd 启动订单监控服务..."
        systemctl start order-checker
        sleep 2
        pid=$(get_pid)
        if [ -n "$pid" ]; then
            echo "$pid" > "$PID_FILE"
            echo "✅ 服务启动成功 (PID: $pid)"
            echo "📄 日志输出至: $LOG_FILE"
            return 0
        fi
    fi

    echo "🚀 正在启动订单监控服务 (nohup 模式)..."
    export PYTHONUNBUFFERED=1
    export HEADLESS=true
    export TZ=Asia/Shanghai

    nohup "$PYTHON_BIN" main.py >> "$LOG_FILE" 2>&1 &
    local new_pid=$!
    echo "$new_pid" > "$PID_FILE"
    sleep 2

    if kill -0 "$new_pid" 2>/dev/null; then
        echo "✅ 服务启动成功 (PID: $new_pid)"
        echo "📄 日志输出至: $LOG_FILE"
    else
        echo "❌ 服务启动失败，请检查日志: $LOG_FILE"
        exit 1
    fi
}

stop() {
    local pid
    pid=$(get_pid)
    if [ -z "$pid" ]; then
        echo "ℹ️  服务未在运行"
        rm -f "$PID_FILE"
        return 0
    fi

    if command -v systemctl &>/dev/null && systemctl is-active --quiet order-checker 2>/dev/null; then
        echo "🛑 正在通过 systemd 停止订单监控服务..."
        systemctl stop order-checker
        rm -f "$PID_FILE"
        echo "✅ 服务已停止"
        return 0
    fi

    echo "🛑 正在停止订单监控服务 (PID: $pid)..."
    kill "$pid" 2>/dev/null || true
    for _ in {1..10}; do
        if ! kill -0 "$pid" 2>/dev/null; then
            break
        fi
        sleep 1
    done

    if kill -0 "$pid" 2>/dev/null; then
        echo "⚠️  强制终止服务..."
        kill -9 "$pid" 2>/dev/null || true
    fi

    rm -f "$PID_FILE"
    echo "✅ 服务已停止"
}

restart() {
    if command -v systemctl &>/dev/null && systemctl is-active --quiet order-checker 2>/dev/null; then
        echo "🔄 正在通过 systemd 重启订单监控服务..."
        systemctl restart order-checker
        sleep 2
        local pid
        pid=$(get_pid)
        if [ -n "$pid" ]; then
            echo "$pid" > "$PID_FILE"
            echo "✅ 服务重启成功 (PID: $pid)"
            return 0
        fi
    fi
    stop
    sleep 1
    start
}

status() {
    local pid
    pid=$(get_pid)
    if [ -n "$pid" ]; then
        echo "🟢 服务运行正常 (PID: $pid)"
        echo "--- 最近 15 行日志 ---"
        tail -n 15 "$LOG_FILE" 2>/dev/null || echo "(暂无日志)"
    else
        echo "🔴 服务未运行"
        if [ -f "$LOG_FILE" ]; then
            echo "--- 最近 5 行日志 ---"
            tail -n 5 "$LOG_FILE" 2>/dev/null
        fi
    fi
}

test_notify() {
    echo "📨 正在发送微信测试通知..."
    "$PYTHON_BIN" main.py --test-notify
}

test_mock_order() {
    echo "📦 正在发送模拟订单测试卡片..."
    "$PYTHON_BIN" main.py --test-order
}

once() {
    echo "🔍 正在执行单次订单检查测试（忽略工作时间限制）..."
    "$PYTHON_BIN" main.py --once
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    test)
        test_notify
        ;;
    test-order)
        test_mock_order
        ;;
    once)
        once
        ;;
    *)
        echo "使用方法: $0 {start|stop|restart|status|test|test-order|once}"
        echo "  start      : 启动后台监控服务"
        echo "  stop       : 停止监控服务"
        echo "  restart    : 重启监控服务"
        echo "  status     : 查看监控服务状态及近期日志"
        echo "  test       : 发送一条测试微信通知（验证连通性）"
        echo "  test-order : 发送一条模拟订单卡片到微信（验证卡片格式）"
        echo "  once       : 立即执行一次订单抓取检查（忽略工作时间限制）"
        exit 1
        ;;
esac
