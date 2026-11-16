import logging
import sys
from logging.handlers import RotatingFileHandler
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from browser_automation import BrowserAutomation
from order_checker import OrderChecker
from notifier import WeChatNotifier
import config

# ──── 日志配置 ────
config.LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        RotatingFileHandler(
            config.LOG_DIR / "app.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        ),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def is_within_work_hours(dt: datetime) -> bool:
    """
    检查当前时间是否在工作时间窗口内（例如 8:00 至 18:00，含 18:00 整点）。
    """
    start_hour = config.WORK_HOUR_START
    end_hour = config.WORK_HOUR_END
    # 例如 8 <= hour < 18，或者正好是 18:00:xx
    return (start_hour <= dt.hour < end_hour) or (
        dt.hour == end_hour and dt.minute == 0
    )


def check_orders(force: bool = False):
    """主任务：检查新订单并推送到微信"""
    now = datetime.now()

    # 工作时间窗口校验
    if not force and not is_within_work_hours(now):
        logger.info(
            f"当前时间 {now.strftime('%H:%M')}，非工作时间（{config.WORK_HOUR_START}:00 - {config.WORK_HOUR_END}:00），跳过本次检查。"
        )
        return

    logger.info("=" * 60)
    logger.info(f"🔍 开始执行订单检查任务 ({now.strftime('%Y-%m-%d %H:%M:%S')})...")

    checker = OrderChecker()
    notifier = WeChatNotifier()
    automation = BrowserAutomation()

    try:
        # 1. 获取上次检查时间
        last_check = checker.get_last_check_time()
        logger.info(f"上次检查基线: {last_check or '无（首次运行）'}")

        # 2. 登录并抓取新订单
        new_orders = automation.login_and_fetch_orders(since=last_check)
        logger.info(f"本次发现新订单数量: {len(new_orders)}")

        # 3. 推送通知
        push_ok = True
        if new_orders:
            push_ok = notifier.send_orders(new_orders)
            if push_ok:
                logger.info(f"📱 成功推送 {len(new_orders)} 条订单至微信")
            else:
                logger.warning("⚠️ 微信推送未成功，请检查 PushPlus Token 配置")
        else:
            logger.info("暂无新增订单")

        # 4. 更新检查时间基线（无新订单 或 推送成功时更新）
        if not new_orders or push_ok:
            checker.update_last_check_time()

    except Exception as e:
        logger.error(f"💥 检查任务异常: {e}", exc_info=True)
        try:
            notifier.send_error(str(e))
        except Exception:
            pass


def main():
    if "--test-notify" in sys.argv:
        logger.info("📌 发送测试通知模式")
        notifier = WeChatNotifier()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        title = "🚀 辽宁医保订单监控 - 服务测试通知"
        content = (
            f'<div style="font-family:sans-serif;padding:15px;border:1px solid #1a73e8;border-radius:8px;">'
            f'<h3 style="color:#1a73e8;margin-top:0;">🎉 监控服务测试通知</h3>'
            f'<p><b>发送时间：</b>{now_str}</p>'
            f'<p><b>系统状态：</b>后台监控服务及浏览器自动化已成功部署就绪</p>'
            f'<p><b>通知渠道：</b>PushPlus 微信推送通道正常</p>'
            f'<hr style="border:none;border-top:1px dashed #ccc;"/>'
            f'<p style="color:#666;font-size:12px;">系统工作时间：每日 08:00 - 18:00（每15分钟检测新订单）。</p>'
            f'</div>'
        )
        ok = notifier._send(title, content)
        if ok:
            logger.info("✅ 测试通知发送成功！请查看微信推送。")
        else:
            logger.error("❌ 测试通知发送失败，请检查 PushPlus 配置。")
        return

    if "--test-order" in sys.argv:
        logger.info("📌 发送模拟订单测试卡片模式")
        notifier = WeChatNotifier()
        mock_orders = [
            {
                "order_no": f"TEST-{datetime.now().strftime('%Y%m%d%H%M')}",
                "amount": "1280.00",
                "hospital": "测试医疗机构（医保定点医院）",
                "send_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "delivery_address": "辽宁省沈阳市测试路100号药库",
                "contact": "李主任",
                "contact_phone": "13800138000",
                "delivery_company": "辽宁省医药配送物流中心",
                "drugs": [
                    {
                        "drug_name": "阿莫西林胶囊",
                        "spec": "0.25g*24粒/盒",
                        "package": "盒",
                        "manufacturer": "某某制药股份有限公司",
                        "price": "12.80",
                        "quantity": "50",
                    },
                    {
                        "drug_name": "布洛芬缓释胶囊",
                        "spec": "0.3g*20粒/盒",
                        "package": "盒",
                        "manufacturer": "某某药业有限公司",
                        "price": "16.00",
                        "quantity": "40",
                    },
                ],
            }
        ]
        ok = notifier.send_orders(mock_orders)
        if ok:
            logger.info("✅ 模拟订单测试卡片发送成功！请查看微信推送。")
        else:
            logger.error("❌ 模拟订单测试卡片发送失败，请检查 PushPlus 配置。")
        return

    if "--once" in sys.argv:
        logger.info("📌 单次运行测试模式（跳过工作时间限制）")
        check_orders(force=True)
        return

    logger.info("🚀 辽宁医保药品交易订单定时提醒服务启动")
    logger.info(
        f"   运行时间: 每日 {config.WORK_HOUR_START}:00 - {config.WORK_HOUR_END}:00"
    )
    logger.info(
        f"   调度规律: 白天每隔 15 分钟 (08:00, 08:15, 08:30, 08:45 ... 18:00)"
    )
    logger.info(f"   无头模式: {config.HEADLESS}")

    # 1. 服务启动时立即执行一次检查（如果在工作时间内）
    if is_within_work_hours(datetime.now()):
        logger.info("⚡ 服务启动，立即执行首次检查...")
        check_orders()
    else:
        logger.info(
            f"⚡ 当前非工作时间（{datetime.now().strftime('%H:%M')}），将在下一个工作节点开始执行。"
        )

    # 2. 启动定时调度器（CronTrigger 精准控制整点与半点）
    scheduler = BlockingScheduler()

    # 每天 8-18 点，每 15 分钟执行一次
    trigger = CronTrigger(
        hour=f"{config.WORK_HOUR_START}-{config.WORK_HOUR_END}",
        minute="0,15,30,45",
    )

    scheduler.add_job(
        check_orders,
        trigger=trigger,
        id="order_check",
        max_instances=1,        # 防止前次未结束导致重叠运行
        misfire_grace_time=300,  # 允许 5 分钟内的延迟补偿
    )

    # 打印接下来的 3 个计划执行时间点
    next_runs = []
    t = datetime.now()
    for _ in range(3):
        t = trigger.get_next_fire_time(t, t)
        if t:
            next_runs.append(t.strftime("%Y-%m-%d %H:%M:%S"))
    logger.info(f"📅 接下来计划触发的时间节点: {next_runs}")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("👋 定时提醒服务已停止")


if __name__ == "__main__":
    main()
