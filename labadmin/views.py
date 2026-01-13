from django.shortcuts import render, redirect, get_object_or_404

from django.db.models import Q
from user.models import UserInfo
from user.forms import UserInfoForm
from django.contrib.auth.hashers import make_password  # 密码加密
from django.contrib.auth import update_session_auth_hash  # 保持登录状态

# 以下是创建角色组和初始用户的代码
from django.contrib.auth.models import User, Group, Permission

from django.contrib.auth.decorators import login_required
from django.contrib import messages

from booking.models import Booking, ApprovalRecord
from user.models import UserInfo
from devices.models import Device


def admin_home(request):
    return render(request, 'admin/home.html')

def device_list(request):
    """
    用户端设备查询视图
    对应路径：/user/device/list/
    """
    # 1. 处理搜索逻辑
    keyword = request.GET.get('keyword', '')
    # 基础查询：获取所有设备（按编号排序）
    devices = Device.objects.all().order_by('device_code')
    
    # 如果有搜索关键词，过滤结果
    if keyword:
        devices = devices.filter(
            Q(device_code__icontains=keyword) |  # 按设备编号搜索
            Q(model__icontains=keyword) |        # 按型号搜索
            Q(manufacturer__icontains=keyword) | # 按厂商搜索
            Q(purpose__icontains=keyword)        # 按实验用途搜索
        )

    # 2. 准备上下文数据
    context = {
        'devices': devices,
        'keyword': keyword,  # 回显搜索关键词
    }
    return render(request, 'user/device_list.html', context)

def booking_apply(request):
    # 模拟提交预约申请后跳转
    if request.method == 'POST':
        return redirect('my_booking')
    return render(request, 'user/booking_apply.html')

def my_booking(request):
    return render(request, 'user/my_booking.html')

def report_stat(request):
    return render(request, 'admin/report_stat.html')

# labadmin/views.py

@login_required
def booking_approve(request):
    """设备预约审批（管理员/负责人通用）"""
    # 1. 角色权限判定
    is_admin = request.user.groups.filter(name='设备管理员').exists()
    is_manager = request.user.groups.filter(name='实验室负责人').exists()
    
    if not is_admin and not is_manager:
        messages.error(request, '您没有审批权限！')
        return redirect('admin_home')

    # 2. 数据筛选逻辑
    if is_admin:
        # 管理员审批：待管理员审批 (pending) 的所有申请
        bookings = Booking.objects.filter(status='pending').order_by('-create_time')
    else:
        # 负责人审批：管理员已批准 (admin_approved) 且 申请人是校外人员 (external)
        bookings = Booking.objects.filter(status='admin_approved', applicant__user_type='external').order_by('-create_time')

    # 3. 处理 POST 审批请求
    if request.method == 'POST':
        # 处理单条审批按钮
        if 'approve' in request.POST:
            handle_approval(request, request.POST.get('approve'), 'approve')
        elif 'reject' in request.POST:
            handle_approval(request, request.POST.get('reject'), 'reject')
        
        # 处理批量审批
        elif 'batch_approve' in request.POST:
            ids = request.POST.getlist('booking_ids')
            for b_id in ids:
                handle_approval(request, b_id, 'approve')
        elif 'batch_reject' in request.POST:
            ids = request.POST.getlist('booking_ids')
            for b_id in ids:
                handle_approval(request, b_id, 'reject')
                
        return redirect('booking_approve')

    # 4. 渲染页面
    return render(request, 'admin/booking_approve.html', {
        'bookings': bookings,
        'is_admin': is_admin,
        'is_manager': is_manager
    })

def handle_approval(request, booking_id, action):
    """核心审批处理逻辑"""
    booking = get_object_or_404(Booking, id=booking_id)
    is_admin = request.user.groups.filter(name='设备管理员').exists()
    
    # 1. 状态流转
    if action == 'approve':
        if is_admin:
            if booking.applicant.user_type in ['student', 'teacher']:
                booking.status = 'manager_approved'
            else:
                booking.status = 'admin_approved' # 校外人员待负责人审
        else:
            booking.status = 'manager_approved' # 负责人终审
    else:
        booking.status = 'admin_rejected' if is_admin else 'manager_rejected'

    booking.save()

    # 2. 【修复点】动态获取对应预约的备注信息
    # 对应模板中的 name="comment_{{ booking.booking_code }}"
    comment_key = f'comment_{booking.booking_code}'
    comment_val = request.POST.get(comment_key, '')
    if not comment_val:
        comment_val = '批量操作' if 'batch' in request.body.decode() else '无备注'

    # 3. 记录日志
    ApprovalRecord.objects.create(
        booking=booking,
        approver=request.user,
        approval_level='admin' if is_admin else 'manager',
        action=action,
        comment=comment_val # 👈 使用动态获取的值
    )
    
    action_text = '批准' if action == 'approve' else '拒绝'
    messages.success(request, f'已{action_text}预约：{booking.booking_code}')
