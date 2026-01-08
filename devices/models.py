from django.db import models
from decimal import Decimal 

# 设备可用状态枚举（匹配你的下拉选项）
DEVICE_STATUS = (
    ('available', '可用'),
    ('unavailable', '不可用'),
)

class Device(models.Model):
    """实验室设备模型（适配现有页面字段）"""
    # 核心字段（与你的页面一一对应）
    device_code = models.CharField(max_length=50, verbose_name='设备编号', unique=True)  # 例如 DEV001
    model = models.CharField(max_length=100, verbose_name='型号')  # 型号A-100
    manufacturer = models.CharField(max_length=100, verbose_name='生产厂商', default='未知厂商')  # 已加默认值
    purchase_date = models.DateField(verbose_name='购入时间', null=True, blank=True)  # 可选：加空值支持
    purpose = models.CharField(max_length=200, verbose_name='实验用途', null=True, blank=True, default='未知用途')  # 可选：加空值支持
    status = models.CharField(max_length=20, choices=DEVICE_STATUS, default='可用', verbose_name='可用状态')
    # 关键修改：给价格字段加默认值（Decimal类型默认值用数字）
    price_internal = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='校内租用价格（元/2小时）', default=Decimal('0'))
    price_external = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='校外租用价格（元/2小时）', default=Decimal('0'))

    # 时间戳（自动生成，无需页面输入）
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '设备'
        verbose_name_plural = '设备管理'
        ordering = ['device_code']  # 按设备编号排序

    def __str__(self):
        return f"{self.device_code} - {self.model}"