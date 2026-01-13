import os
import django

# 配置 Django 环境（必须）
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jnu_lab_system.settings')  # 替换为实际项目名
django.setup()

# 以下是创建角色组和初始用户的代码
from django.contrib.auth.models import User, Group, Permission
from django.contrib.auth.hashers import make_password  # 密码加密
from devices.models import Device
from user.models import UserInfo

def create_roles_and_users():
    # ====================== 第一步：创建角色组 ======================
    admin_group, created = Group.objects.get_or_create(name='设备管理员')
    manager_group, created = Group.objects.get_or_create(name='实验室负责人')
    user_group, created = Group.objects.get_or_create(name='普通用户')
    print(f"角色组创建状态：设备管理员({created}), 实验室负责人({created}), 普通用户({created})")

    # 分配权限
    admin_perms = Permission.objects.filter(content_type__model__in=['device'])
    admin_group.permissions.set(admin_perms)
    manager_perms = Permission.objects.filter(content_type__model__in=['userinfo'])
    manager_group.permissions.set(manager_perms)

    # ====================== 第二步：创建初始用户 ======================
    # 1. 创建设备管理员用户：labadmin（密码=labadmin）【保持不变】
    labadmin_user, created = User.objects.get_or_create(
        username='labadmin',
        defaults={
            'password': make_password('labadmin'),
            'first_name': '设备管理员',
            'is_staff': True,
            'is_active': True
        }
    )
    labadmin_user.groups.add(admin_group)
    labadmin_user.save()
    print(f"设备管理员用户 labadmin 创建状态：{created}")

    # 2. 创建实验室负责人用户：manager（密码=manager）【保持不变】
    manager_user, created = User.objects.get_or_create(
        username='manager',
        defaults={
            'password': make_password('manager'),
            'first_name': '实验室负责人',
            'is_staff': True,
            'is_active': True
        }
    )
    manager_user.groups.add(manager_group)
    manager_user.save()
    print(f"实验室负责人用户 manager 创建状态：{created}")

    
    print("\n===== 初始化完成 =====")
    print("初始用户列表：")
    print(f"1. 设备管理员：用户名=labadmin，密码=labadmin（角色：设备管理员）")
    print(f"2. 实验室负责人：用户名=manager，密码=manager（角色：实验室负责人）")

if __name__ == '__main__':
    create_roles_and_users()