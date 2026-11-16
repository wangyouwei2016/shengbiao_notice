import ddddocr
import logging

logger = logging.getLogger(__name__)


class CaptchaSolver:
    def __init__(self):
        self.ocr = ddddocr.DdddOcr(show_ad=False)

    def solve(self, image_bytes: bytes) -> str:
        """
        识别4位字母数字验证码。
        目标样式：灰底黑字，轻微噪点扭曲（如 "by3b"）。
        """
        result = self.ocr.classification(image_bytes)
        cleaned = result.strip()
        logger.info(f"验证码 OCR: '{result}' -> '{cleaned}'")
        return cleaned
