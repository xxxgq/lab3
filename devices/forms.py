from django import forms
from .models import Device

class DeviceForm(forms.ModelForm):
    """设备新增/编辑表单（适配现有页面字段）"""
    class Meta:
        model = Device
        # 排除自动生成的时间戳字段，其余字段全部包含
        exclude = ['created_at', 'updated_at']
        # 自定义控件（可选，主要是为了适配你页面的样式）
        widgets = {
            'purchase_date': forms.DateInput(attrs={'type': 'date'}),
            # 如果你需要给输入框加 class 样式，可以在这里添加
            'device_code': forms.TextInput(attrs={'placeholder': '例如：DEV003', 'required': 'required'}),
            'model': forms.TextInput(attrs={'required': 'required'}),
            'manufacturer': forms.TextInput(attrs={'required': 'required'}),
            'purpose': forms.TextInput(attrs={'required': 'required'}),
        }