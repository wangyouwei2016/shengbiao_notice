import logging
import time
from datetime import datetime
from playwright.sync_api import sync_playwright, Page
from captcha_solver import CaptchaSolver
import config

logger = logging.getLogger(__name__)


class BrowserAutomation:
    def __init__(self):
        self.solver = CaptchaSolver()

    def login_and_fetch_orders(self, since: str | None = None) -> list[dict]:
        """
        登录并获取新订单的完整信息。

        Args:
            since: 上次检查时间 "YYYY-MM-DD HH:MM:SS"。
                   如果为 None，则只获取当天的前 10 条订单作为基线。
        Returns:
            新订单列表，每个订单包含完整的 10 个字段 + 药品明细。
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=config.HEADLESS,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            context = browser.new_context(
                viewport={"width": 1440, "height": 900},
                ignore_https_errors=True,
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()

            try:
                # Step 1: 登录
                if not self._login(page):
                    logger.error("❌ 登录未能成功，放弃本次检查")
                    return []

                # Step 2: 关闭首页弹窗并导航到「发货退货管理 -> 按订单发货」
                if not self._navigate_to_order_list(page):
                    logger.error("❌ 导航到订单列表失败")
                    return []

                # Step 3: 扫描新订单
                orders = self._fetch_new_orders(page, since)
                return orders

            except Exception as e:
                logger.error(f"自动化异常: {e}", exc_info=True)
                try:
                    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
                    page.screenshot(
                        path=str(config.LOG_DIR / "error_screenshot.png")
                    )
                    logger.info("已保存错误截图到 logs/error_screenshot.png")
                except Exception:
                    pass
                return []
            finally:
                browser.close()

    # ──────────────────────────────────────────────
    #  登录
    # ──────────────────────────────────────────────

    def _login(self, page: Page) -> bool:
        """登录流程：账号密码 + OCR 验证码，失败自动重试。"""
        logger.info(f"正在访问登录页面: {config.LOGIN_URL}")
        page.goto(config.LOGIN_URL, timeout=60000, wait_until="domcontentloaded")
        time.sleep(2)

        for attempt in range(config.CAPTCHA_MAX_RETRIES):
            logger.info(
                f"🔑 正在尝试登录 (第 {attempt + 1}/{config.CAPTCHA_MAX_RETRIES} 次)..."
            )

            # 定位输入框
            user_input = page.locator('input[placeholder="请输入账号"]')
            pwd_input = page.locator('input[placeholder="请输入密码"]')
            code_input = page.locator('input[placeholder="请输入验证码"]')

            user_input.wait_for(state="visible", timeout=10000)

            # 填写用户名与密码
            user_input.fill("")
            user_input.fill(config.USERNAME)
            pwd_input.fill("")
            pwd_input.fill(config.PASSWORD)

            # 定位验证码图片
            captcha_img = page.locator("img.img-box").first
            if not captcha_img.is_visible():
                # 备用定位
                captcha_img = page.locator('img[src*="data:image"]').first

            if not captcha_img.is_visible():
                logger.error("无法找到验证码图片元素")
                return False

            # OCR 识别
            captcha_bytes = captcha_img.screenshot()
            captcha_text = self.solver.solve(captcha_bytes)
            logger.info(f"验证码 OCR 结果: {captcha_text}")

            if not captcha_text:
                logger.warning("验证码识别为空，点击刷新")
                captcha_img.click()
                time.sleep(1.5)
                continue

            # 填入验证码
            code_input.fill("")
            code_input.fill(captcha_text)

            # 点击登录
            login_btn = page.locator(
                'button.el-button--primary:has-text("登录")'
            ).first
            login_btn.click()
            time.sleep(3)

            # 判断是否登录成功
            # 成功标志：出现“退出”或“辽宁药品”或者“您好”
            is_logged_in = False
            for selector in [
                "text=退出",
                "text=药品交易结算",
                "text=提醒列表",
            ]:
                if page.locator(selector).first.is_visible():
                    is_logged_in = True
                    break

            if is_logged_in:
                logger.info("✅ 登录成功！")
                return True

            # 检查是否有错误弹窗
            msg_el = page.locator(".el-message__content").first
            if msg_el.is_visible():
                try:
                    logger.warning(f"系统提示: {msg_el.inner_text()}")
                except Exception:
                    pass

            logger.warning("登录未跳转，准备刷新验证码重试...")
            try:
                captcha_img.click()
            except Exception:
                pass
            time.sleep(1.5)

        logger.error("❌ 验证码多次识别失败，达到最大重试次数")
        config.LOG_DIR.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(config.LOG_DIR / "login_failed.png"))
        return False

    # ──────────────────────────────────────────────
    #  导航
    # ──────────────────────────────────────────────

    def _navigate_to_order_list(self, page: Page) -> bool:
        """导航: 关闭弹窗 -> 药品交易结算 -> 发货退货管理 -> 按订单发货"""
        logger.info("正在导航到订单发货页面...")

        # 1. 关闭首页提醒弹窗（如“提醒列表”、“关闭”等）
        for close_text in ["关闭", "取 消", "确 定"]:
            btn = page.locator(f'button:has-text("{close_text}")').first
            if btn.is_visible():
                try:
                    btn.click()
                    time.sleep(1)
                except Exception:
                    pass

        # 2. 点击「药品交易结算」
        trade_menu = page.locator("text=药品交易结算").first
        trade_menu.wait_for(state="visible", timeout=10000)
        trade_menu.click()
        time.sleep(1.5)

        # 3. 点击「发货退货管理」
        delivery_menu = page.locator("text=发货退货管理").first
        delivery_menu.wait_for(state="visible", timeout=10000)
        delivery_menu.click()
        time.sleep(1)

        # 4. 点击「按订单发货」
        sub_menu = page.locator("text=按订单发货").first
        sub_menu.wait_for(state="visible", timeout=10000)
        sub_menu.click()
        time.sleep(3)

        # 验证是否到达发货管理页面
        if page.locator(".el-table__body").first.is_visible():
            logger.info("✅ 已到达发货管理（按订单发货）列表页面")
            return True

        logger.error("未能加载订单列表表格")
        return False

    # ──────────────────────────────────────────────
    #  订单抓取
    # ──────────────────────────────────────────────

    def _fetch_new_orders(
        self, page: Page, since: str | None
    ) -> list[dict]:
        """
        从列表页按发送时间（倒序排列）扫描订单。
        遇到发送时间 <= since 的条目时立即终止扫描。
        对每个新订单，点击其订单编号进入详情页抓取完整信息。
        """
        orders = []

        # 确认表格加载
        try:
            page.locator(".el-table__body tbody tr").first.wait_for(
                state="visible", timeout=10000
            )
        except Exception:
            logger.info("列表无数据或加载超时")
            return []

        rows = page.locator(".el-table__body tbody tr").all()
        total_rows = len(rows)
        logger.info(f"当前列表页共有 {total_rows} 条记录")

        since_dt = None
        if since:
            try:
                since_dt = datetime.strptime(since, "%Y-%m-%d %H:%M:%S")
                logger.info(f"基准比对时间: {since_dt}")
            except Exception as e:
                logger.warning(f"解析 since 时间失败: {e}")

        # 记录待进入详情的行索引
        new_indices = []

        for idx, row in enumerate(rows):
            tds = row.locator("td").all()
            if len(tds) < 7:
                continue

            order_no = tds[1].inner_text().strip()
            hospital = tds[2].inner_text().strip()
            amount = tds[3].inner_text().strip()
            send_time_str = tds[5].inner_text().strip()

            try:
                send_dt = datetime.strptime(
                    send_time_str, "%Y-%m-%d %H:%M:%S"
                )
            except Exception:
                logger.warning(f"无法解析时间: {send_time_str}")
                continue

            # 如果存在基线时间，且当前订单时间 <= 基线时间，则因为是倒序排列，后续订单肯定更早，直接终止！
            if since_dt and send_dt <= since_dt:
                logger.info(
                    f"条目 [{order_no}] 时间 {send_time_str} <= 上次检查时间 {since}，停止扫描后续记录。"
                )
                break

            logger.info(
                f"🆕 发现新订单: {order_no} | {hospital} | 金额: ¥{amount} | 发送时间: {send_time_str}"
            )
            new_indices.append(idx)

            # 如果是首次运行（since 为 None），避免一次性推送所有历史订单，只取最新一条或者当天的订单
            if since_dt is None:
                # 首次运行，只取第 1 条作为测试/初始
                logger.info("首次运行无历史检查记录，将仅处理最新的 1 条订单")
                break

        # 逐个点击进入详情页抓取完整信息
        for row_idx in new_indices:
            try:
                # 重新定位行（防止页面刷新后元素失效）
                curr_rows = page.locator(".el-table__body tbody tr").all()
                if row_idx >= len(curr_rows):
                    break
                target_row = curr_rows[row_idx]

                # 点击订单编号按钮进入详情
                order_btn = (
                    target_row.locator("td").nth(1).locator("button").first
                )
                order_btn.click()
                time.sleep(2.5)

                # 解析详情
                order_data = self._parse_order_detail(page)
                if order_data:
                    orders.append(order_data)

                # 点击返回按钮返回列表
                back_btn = page.locator('button:has-text("返回")').first
                if back_btn.is_visible():
                    back_btn.click()
                    time.sleep(2)
                else:
                    logger.warning("未找到返回按钮，尝试重新进入菜单")
                    self._navigate_to_order_list(page)

            except Exception as e:
                logger.error(f"处理订单索引 {row_idx} 详情失败: {e}")
                # 尝试点击返回或者刷新
                try:
                    page.locator('button:has-text("返回")').first.click()
                    time.sleep(2)
                except Exception:
                    pass

        return orders

    # ──────────────────────────────────────────────
    #  详情页解析
    # ──────────────────────────────────────────────

    def _parse_order_detail(self, page: Page) -> dict | None:
        """
        从订单详情视图提取 10 个字段及药品明细。
        """
        try:

            def get_field(label: str) -> str:
                """通过 label 标签提取对应的字段内容"""
                el = page.locator(f'label:has-text("{label}")').first
                if el.is_visible():
                    parent = el.locator("..")
                    content_el = parent.locator(
                        ".el-form-item__content, div"
                    ).last
                    return content_el.inner_text().strip()
                return ""

            order = {
                "order_no": get_field("订单编号："),
                "amount": get_field("订单金额："),
                "hospital": get_field("医疗机构："),
                "send_time": get_field("发送时间："),
                "delivery_address": get_field("收货地址："),
                "contact": get_field("联系人："),
                "contact_phone": get_field("联系人电话："),
                "delivery_company": get_field("配送企业："),
            }

            # 抓取药品明细表格
            drugs = []
            tables = page.locator("table").all()
            # Table 1 是明细数据表格
            if len(tables) >= 2:
                detail_table = tables[1]
                rows = detail_table.locator("tr").all()
                for r in rows:
                    tds = [
                        td.inner_text().strip()
                        for td in r.locator("td").all()
                    ]
                    # 列定义：
                    # 2: 通用名/商品名
                    # 3: 规格
                    # 4: 包装
                    # 5: 生产企业
                    # 6: 采购价(元)
                    # 7: 采购数量
                    if len(tds) >= 8:
                        drugs.append(
                            {
                                "drug_name": tds[2],
                                "spec": tds[3],
                                "package": tds[4],
                                "manufacturer": tds[5],
                                "price": tds[6],
                                "quantity": tds[7],
                            }
                        )

            order["drugs"] = drugs
            logger.info(
                f"✅ 成功抓取订单: {order['order_no']} | 机构: {order['hospital']} | 包含 {len(drugs)} 种药品"
            )
            return order

        except Exception as e:
            logger.error(f"解析详情视图失败: {e}", exc_info=True)
            return None
