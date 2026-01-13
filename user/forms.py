from django import forms
from django.contrib.auth.hashers import make_password
from .models import UserInfo

class UserInfoForm(forms.ModelForm):
    """用户信息新增/编辑表单"""
    # 【新增】密码重置字段（可选，编辑时显示）
    reset_password = forms.CharField(
        max_length=50, 
        required=False, 
        label='重置密码（留空则不修改）',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = UserInfo
        fields = ['user_code', 'name', 'user_type', 'department', 'phone', 'is_active']
        labels = {
            'is_active': '借用资格（勾选=正常，取消=禁用）',
        }
        widgets = {
            'user_code': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'user_type': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def save(self, commit=True):
        user_info = super().save(commit=False)
        
        # 如果填写了重置密码，更新登录账号的密码
        reset_pwd = self.cleaned_data.get('reset_password')
        if reset_pwd and user_info.auth_user:
            user_info.auth_user.password = make_password(reset_pwd)
            user_info.auth_user.save()
        
        if commit:
            user_info.save()
        return user_info