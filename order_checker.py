import json
import logging
from datetime import datetime
import config

logger = logging.getLogger(__name__)


class OrderChecker:
    def __init__(self):
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)

    def get_last_check_time(self) -> str | None:
        """获取上次检查时间字符串 'YYYY-MM-DD HH:MM:SS'"""
        try:
            if config.LAST_CHECK_FILE.exists():
                content = config.LAST_CHECK_FILE.read_text(
                    encoding="utf-8"
                ).strip()
                if not content:
                    return None
                data = json.loads(content)
                val = data.get("last_check_time")
                if val and isinstance(val, str):
                    return val.strip()
        except Exception as e:
            logger.warning(f"读取 last_check 失败: {e}")
        return None

    def update_last_check_time(self, custom_time: str | None = None):
        """原子写入更新为当前时间"""
        now = custom_time or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tmp_file = config.LAST_CHECK_FILE.with_suffix(".tmp")
        tmp_file.write_text(
            json.dumps({"last_check_time": now}, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp_file.replace(config.LAST_CHECK_FILE)
        logger.info(f"✅ 检查时间已更新: {now}")
