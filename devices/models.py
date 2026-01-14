from django.db import models
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth import get_user_model

# 设备可用状态枚举
DEVICE_STATUS = (
    ('available', '可用'),
    ('unavailable', '不可用'),
)

class Device(models.Model):
    """实验室设备模型（整合了详细字段与台账自动记录功能）"""
    
    # --- 基础信息字段 (保留你的编写) ---
    device_code = models.CharField(max_length=50, verbose_name='设备编号', unique=True)
    model = models.CharField(max_length=100, verbose_name='型号')
    manufacturer = models.CharField(max_length=100, verbose_name='生产厂商', default='未知厂商')
    purchase_date = models.DateField(verbose_name='购入时间', null=True, blank=True)
    purpose = models.CharField(max_length=200, verbose_name='实验用途', null=True, blank=True, default='未知用途')
    status = models.CharField(max_length=20, choices=DEVICE_STATUS, default='可用', verbose_name='可用状态')
    
    # 价格字段
    price_internal = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='校内租用价格（元/2小时）', default=Decimal('0'))
    price_external = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='校外租用价格（元/2小时）', default=Decimal('0'))

    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '设备'
        verbose_name_plural = '设备管理'
        ordering = ['device_code']

    def __str__(self):
        return f"{self.device_code} - {self.model}"

    # --- 业务逻辑：台账自动记录 (整合他人增加的功能) ---

    def save(self, *args, **kwargs):
        """重写save方法，自动记录设备操作到台账"""
        # 局部导入防止循环引用
        from ledger.models import DeviceLedger

        is_new = self.pk is None
        old_status = None

        if not is_new:
            try:
                old_device = Device.objects.get(pk=self.pk)
                old_status = old_device.status
            except Device.DoesNotExist:
                pass

        # 执行保存逻辑
        super().save(*args, **kwargs)

        # 获取操作人（默认取第一个管理员作为记录，建议后续在View层传递request.user）
        User = get_user_model()
        current_user = None
        try:
            current_user = User.objects.filter(is_staff=True).first()
        except Exception:
            pass

        # 1. 记录新增设备操作
        if is_new:
            DeviceLedger.objects.create(
                device=self,
                device_name=self.model,
                operation_type='other',
                operation_date=timezone.now(),
                status_after_operation=self.status,
                description=f'新增设备：{self.device_code} - {self.model}',
                operator=current_user
            )
        # 2. 记录状态变更操作
        elif old_status and old_status != self.status:
            # 只有状态发生实际变化才记录
            DeviceLedger.objects.create(
                device=self,
                device_name=self.model,
                operation_type='other',
                operation_date=timezone.now(),
                status_after_operation=self.status,
                description=f'设备状态变更：{old_status} → {self.status}',
                operator=current_user
            )

    def delete(self, *args, **kwargs):
        """重写delete方法，记录设备报废/删除操作"""
        from ledger.models import DeviceLedger

        User = get_user_model()
        current_user = None
        try:
            current_user = User.objects.filter(is_staff=True).first()
        except Exception:
            pass

        # 删除前创建台账记录
        DeviceLedger.objects.create(
            device=None,  # 设备即将删除，外键可能需设为null
            device_name=f"{self.device_code} - {self.model} (已删除)",
            operation_type='discard',
            operation_date=timezone.now(),
            status_after_operation='discarded',
            description=f'删除设备：{self.device_code} - {self.model}',
            operator=current_user
        )

        super().delete(*args, **kwargs)