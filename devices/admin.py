# manager/admin.py
from django.contrib import admin
from .models import Device

# 自定义 Device 模型在 admin 后台的显示样式
@admin.register(Device)  # 装饰器方式注册，和 admin.site.register(Device, DeviceAdmin) 效果一致
class DeviceAdmin(admin.ModelAdmin):
    # 列表页显示的字段
    list_display = [
        'device_code', 'model', 'manufacturer', 'status', 
        'price_internal', 'price_external', 'purchase_date'
    ]
    
    # 支持搜索的字段（按设备编号、型号、厂商搜索）
    search_fields = ['device_code', 'model', 'manufacturer']
    
    # 右侧筛选栏（按状态筛选）
    list_filter = ['status']
    
    # 排序方式（默认按设备编号升序）
    ordering = ['device_code']
    
    # 只读字段（创建/更新时间自动生成，设为只读）
    readonly_fields = ['created_at', 'updated_at']
    
    # 编辑页字段分组（让表单更整洁）
    fieldsets = (
        ('设备基础信息', {
            'fields': ('device_code', 'model', 'manufacturer', 'purchase_date', 'purpose', 'status')
        }),
        ('租用价格信息', {
            'fields': ('price_internal', 'price_external')
        }),
        ('系统自动记录', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)  # 可折叠分组
        }),
    )