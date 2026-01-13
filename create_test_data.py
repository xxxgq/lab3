import os
import django
from django.contrib.auth.hashers import make_password

# 1. 配置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jnu_lab_system.settings')
django.setup()

from django.contrib.auth.models import User, Group
from devices.models import Device
from user.models import UserInfo

def create_test_records():
    # 获取或创建“普通用户”组
    user_group, _ = Group.objects.get_or_create(name='普通用户')

    # 2. 创建一个测试设备
    device, _ = Device.objects.get_or_create(
        device_code='DEV001',
        defaults={'model': '激光切割机', 'status': '可用', 'manufacturer': '江南精密'}
    )
    print(f"设备创建成功: {device.device_code}")

    # 3. 创建测试教师 (指导教师)
    user_t, created = User.objects.get_or_create(
        username='2001',
        defaults={'password': make_password('2001'), 'is_active': True}
    )
    if created:
        UserInfo.objects.create(
            auth_user=user_t,
            user_type='teacher',
            user_code='2001',
            name='王老师',
            department='机械学院'
        )
        user_t.groups.add(user_group)
    print(f"教师创建成功: 王老师 (工号: 2001)")

    # 4. 创建测试学生
    user_s, created = User.objects.get_or_create(
        username='1001',
        defaults={'password': make_password('1001'), 'is_active': True}
    )
    if created:
        UserInfo.objects.create(
            auth_user=user_s,
            user_type='student',
            user_code='1001',
            name='张同学',
            department='机械学院',
            advisor='王老师' # 建立指导关系
        )
        user_s.groups.add(user_group)
    print(f"学生创建成功: 张同学 (学号: 1001)")
# 在 create_test_data.py 中添加
def create_external_test_user():
    user_group, _ = Group.objects.get_or_create(name='普通用户')
    
    # 1. 创建校外人员账号
    user_e, created = User.objects.get_or_create(
        username='9001',
        defaults={'password': make_password('9001'), 'is_active': True}
    )
    if created:
        UserInfo.objects.create(
            auth_user=user_e,
            user_type='external',  # 👈 关键：身份设为校外人员
            user_code='9001',
            name='校外某公司',
            department='校外单位',
            company_address='江南路100号',
            position='技术负责人'
        )
        user_e.groups.add(user_group)
    print(f"校外人员创建成功: 用户名=9001, 密码=9001")

if __name__ == '__main__':
    create_external_test_user()

if __name__ == '__main__':
    create_test_records()
