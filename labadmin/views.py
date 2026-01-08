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

# 1. 管理员审批页面
@login_required
def booking_approve(request):
    """设备预约审批（管理员）"""
    # 校验是否是管理员/负责人
    is_admin = request.user.groups.filter(name='设备管理员').exists()
    is_manager = request.user.groups.filter(name='实验室负责人').exists()
    if not is_admin and not is_manager:
        messages.error(request, '你无审批权限！')
        return redirect('manager_home')
    
    # 获取筛选条件
    user_type_filter = request.GET.get('user_type', 'all')
    
    # 核心修改：管理员只看「待审批（pending）」的申请，不看「已批准待负责人审批（admin_approved）」的
    if is_admin:
        # 管理员仅审批：待审批的申请（移除 admin_approved）
        bookings = Booking.objects.filter(
            status='pending'  # 只保留待管理员审批的
        ).order_by('-create_time')
    else:
        # 负责人仍只审批：管理员已批准的校外人员申请（admin_approved + external）
        bookings = Booking.objects.filter(
            status='admin_approved',
            applicant__user_type='external'
        ).order_by('-create_time')
    
    # 筛选用户类型
    if user_type_filter != 'all':
        if user_type_filter == 'student':
            bookings = bookings.filter(applicant__user_type='student')
        elif user_type_filter == 'teacher':
            bookings = bookings.filter(applicant__user_type='teacher')
        elif user_type_filter == 'external':
            bookings = bookings.filter(applicant__user_type='external')
    
    # 处理审批操作（原有逻辑不变）
    if request.method == 'POST':
        # 单个审批
        if 'approve' in request.POST:
            booking_id = request.POST.get('approve')
            handle_approval(request, booking_id, 'approve')
        elif 'reject' in request.POST:
            booking_id = request.POST.get('reject')
            handle_approval(request, booking_id, 'reject')
        
        # 批量审批（简化版）
        elif 'batch_approve' in request.POST or 'batch_reject' in request.POST:
            booking_ids = request.POST.getlist('booking_ids')
            action = 'approve' if 'batch_approve' in request.POST else 'reject'
            for booking_id in booking_ids:
                handle_approval(request, booking_id, action)
        
        return redirect('booking_approve')
    
    context = {
        'bookings': bookings,
        'user_type_filter': user_type_filter,
        'is_admin': is_admin,
        'is_manager': is_manager
    }
    return render(request, 'admin/booking_approve.html', context)

def handle_approval(request, booking_id, action):
    """处理审批逻辑（核心）"""
    booking = get_object_or_404(Booking, id=booking_id)
    is_admin = request.user.groups.filter(name='设备管理员').exists()
    is_manager = request.user.groups.filter(name='实验室负责人').exists()
    
    # 1. 管理员审批逻辑
    if is_admin:
        if action == 'approve':
            # 学生/教师：直接审批通过
            if booking.applicant.user_type in ['student', 'teacher']:
                booking.status = 'manager_approved'
            # 校外人员：需负责人审批
            else:
                booking.status = 'admin_approved'
            approval_level = 'admin'
        else:
            booking.status = 'admin_rejected'
            approval_level = 'admin'
    
    # 2. 负责人审批逻辑（仅校外人员）
    elif is_manager:
        if action == 'approve':
            booking.status = 'manager_approved'
        else:
            booking.status = 'manager_rejected'
        approval_level = 'manager'
    
    # 保存预约状态
    booking.save()
    
    # 记录审批日志
    ApprovalRecord.objects.create(
        booking=booking,
        approver=request.user,
        approval_level=approval_level,
        action=action,
        comment=request.POST.get(f'comment_{booking.booking_code}', '')  # 可扩展审批备注
    )
    
    # 提示信息
    action_text = '批准' if action == 'approve' else '拒绝'
    messages.success(request, f'已{action_text}预约申请：{booking.booking_code}')
