import requests
import logging
from datetime import datetime
import config

logger = logging.getLogger(__name__)


class WeChatNotifier:
    def __init__(self):
        self.token = config.PUSHPLUS_TOKEN
        self.to = config.PUSHPLUS_TO
        self.url = config.PUSHPLUS_URL

    def send_orders(self, orders: list[dict]) -> bool:
        """推送新订单到微信，返回是否成功。"""
        if not orders:
            return True
        title = f"📦 新增 {len(orders)} 条发货订单"
        content = self._build_html(orders)
        return self._send(title, content)

    def send_error(self, error_msg: str) -> bool:
        """推送错误告警"""
        title = "⚠️ 辽宁医保订单监控异常"
        content = (
            '<div style="color:red;padding:10px;border:1px solid red;'
            'border-radius:5px;">'
            f'<p><b>时间：</b>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>'
            f"<p><b>错误信息：</b>{error_msg}</p>"
            "</div>"
        )
        return self._send(title, content)

    def _build_html(self, orders: list[dict]) -> str:
        """构建推送消息的 HTML 内容"""
        html = (
            f'<p style="color:#666;">检测时间：'
            f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>'
            f'<p>共检测到 <b>{len(orders)}</b> 条新订单：</p><hr/>'
        )

        for i, order in enumerate(orders, 1):
            drugs_html = ""
            for drug in order.get("drugs", []):
                drugs_html += (
                    f'<li><b>{drug.get("drug_name", "-")}</b> '
                    f'({drug.get("spec", "")} / {drug.get("package", "")})<br/>'
                    f'生产企业: {drug.get("manufacturer", "-")}<br/>'
                    f'采购单价: ¥{drug.get("price", "-")} | '
                    f'数量: {drug.get("quantity", "-")}</li>'
                )

            html += f"""
            <div style="border:1px solid #e0e0e0;border-radius:8px;
                        padding:12px;margin:12px 0;background:#fafafa;font-family:sans-serif;">
                <h3 style="color:#1a73e8;margin:0 0 10px 0;">📋 订单 {i}</h3>
                <table style="width:100%;border-collapse:collapse;font-size:14px;line-height:1.6;">
                    <tr>
                        <td style="padding:4px 8px;color:#888;width:90px;">订单编号</td>
                        <td style="padding:4px 8px;"><b>{order.get("order_no", "-")}</b></td>
                    </tr>
                    <tr>
                        <td style="padding:4px 8px;color:#888;">订单金额</td>
                        <td style="padding:4px 8px;color:#d93025;font-weight:bold;">¥{order.get("amount", "-")}</td>
                    </tr>
                    <tr>
                        <td style="padding:4px 8px;color:#888;">医疗机构</td>
                        <td style="padding:4px 8px;">{order.get("hospital", "-")}</td>
                    </tr>
                    <tr>
                        <td style="padding:4px 8px;color:#888;">发送时间</td>
                        <td style="padding:4px 8px;">{order.get("send_time", "-")}</td>
                    </tr>
                    <tr>
                        <td style="padding:4px 8px;color:#888;">收货地址</td>
                        <td style="padding:4px 8px;">{order.get("delivery_address", "-")}</td>
                    </tr>
                    <tr>
                        <td style="padding:4px 8px;color:#888;">联系方式</td>
                        <td style="padding:4px 8px;">
                            {order.get("contact", "-")} ({order.get("contact_phone", "-")})
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:4px 8px;color:#888;">配送企业</td>
                        <td style="padding:4px 8px;">{order.get("delivery_company", "-")}</td>
                    </tr>
                </table>
                <div style="margin-top:10px;padding-top:8px;border-top:1px dashed #ccc;">
                    <p style="margin:0 0 4px 0;font-weight:bold;color:#333;">💊 药品明细：</p>
                    <ul style="margin:0;padding-left:20px;font-size:13px;color:#444;">
                        {drugs_html if drugs_html else "<li>无药品明细</li>"}
                    </ul>
                </div>
            </div>
            """

        return html

    def _send(self, title: str, content: str) -> bool:
        """调用 PushPlus API"""
        if not self.token:
            logger.warning("未配置 PUSHPLUS_TOKEN，跳过推送")
            return False

        payload = {
            "token": self.token,
            "title": title,
            "content": content,
            "template": "html",
        }
        if self.to:
            payload["to"] = self.to
        try:
            resp = requests.post(self.url, json=payload, timeout=15)
            result = resp.json()
            if result.get("code") == 200:
                logger.info(f"✅ PushPlus 微信推送成功! 消息流水号: {result.get('data')}")
                return True
            else:
                logger.error(
                    f"❌ PushPlus 微信推送失败! code: {result.get('code')}, msg: {result.get('msg')}"
                )
                return False
        except Exception as e:
            logger.error(f"❌ PushPlus 请求异常: {e}")
            return False
