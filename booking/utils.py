import datetime
from .models import Booking

def generate_booking_code():
    """生成预约编号：BOOK + 年月日 + 序号（如 BOOK20260101001）"""
    today = datetime.date.today().strftime("%Y%m%d")
    # 统计今日已生成的预约数
    count = Booking.objects.filter(booking_code__startswith=f"BOOK{today}").count() + 1
    # 补零到3位
    serial_num = str(count).zfill(3)
    return f"BOOK{today}{serial_num}"