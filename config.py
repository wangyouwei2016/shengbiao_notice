import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent

# 网站
LOGIN_URL = os.getenv("YBJ_LOGIN_URL", "https://ggfw.ybj.ln.gov.cn/tps-web/")
USERNAME = os.getenv("YBJ_USERNAME")
PASSWORD = os.getenv("YBJ_PASSWORD")

# PushPlus
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN")
PUSHPLUS_TO = os.getenv("PUSHPLUS_TO", "")
PUSHPLUS_URL = "https://www.pushplus.plus/send"

# 调度
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "15"))
WORK_HOUR_START = int(os.getenv("WORK_HOUR_START", "8"))
WORK_HOUR_END = int(os.getenv("WORK_HOUR_END", "18"))
CAPTCHA_MAX_RETRIES = int(os.getenv("CAPTCHA_MAX_RETRIES", "5"))

# 浏览器
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"

# 路径
DATA_DIR = BASE_DIR / "data"
LAST_CHECK_FILE = DATA_DIR / "last_check.json"
LOG_DIR = BASE_DIR / "logs"
