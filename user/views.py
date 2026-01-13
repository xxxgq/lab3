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



@login_required
def user_profile(request):
    """个人信息管理视图"""
    # 获取当前登录用户关联的UserInfo
    try:
        user_info = UserInfo.objects.get(auth_user=request.user)
    except UserInfo.DoesNotExist:
        messages.error(request, '未找到你的个人信息，请联系管理员！')
        return redirect('user_home')
    
    # 教师用户：获取指导的学生列表（需提前建立指导关系，此处示例为按advisor字段匹配）
    advisor_students = []
    if user_info.user_type == 'teacher':
        advisor_students = UserInfo.objects.filter(
            user_type='student', 
            advisor__contains=user_info.name
        )
    
    # 处理表单提交
    if request.method == 'POST':
        # 更新基础信息
        user_info.name = request.POST.get('name')
        user_info.gender = request.POST.get('gender')
        user_info.department = request.POST.get('department')
        user_info.phone = request.POST.get('phone')
        
        # 更新不同用户类型的专属字段
        if user_info.user_type == 'student':
            user_info.major = request.POST.get('major')
            user_info.advisor = request.POST.get('advisor')
        elif user_info.user_type == 'teacher':
            user_info.title = request.POST.get('title')
            user_info.research_field = request.POST.get('research_field')
        elif user_info.user_type == 'external':
            user_info.position = request.POST.get('position')
            user_info.company_address = request.POST.get('company_address')
        
        user_info.save()
        messages.success(request, '个人信息修改成功！')
        return redirect('user_profile')
    
    # GET请求：渲染页面
    context = {
        'user_info': user_info,
        'advisor_students': advisor_students
    }
    return render(request, 'user/user_profile.html', context)

# 新增：修改密码视图（简单版）
@login_required
def change_password(request):
    """修改密码视图（完整版）"""
    # 如果是POST请求（提交改密表单）
    if request.method == 'POST':
        old_password = request.POST.get('old_password', '').strip()
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        
        # 1. 空值校验
        if not old_password or not new_password or not confirm_password:
            messages.error(request, '请填写所有密码字段！')
            return render(request, 'user/change_password.html')
        
        # 2. 验证原密码是否正确
        if not request.user.check_password(old_password):
            messages.error(request, '原密码输入错误，请重新输入！')
            return render(request, 'user/change_password.html')
        
        # 3. 验证新密码长度
        # if len(new_password) < 6:
        #     messages.error(request, '新密码长度不能少于6位！')
        #     return render(request, 'user/change_password.html')
        
        # 4. 验证两次新密码是否一致
        if new_password != confirm_password:
            messages.error(request, '两次输入的新密码不一致！')
            return render(request, 'user/change_password.html')
        
        # 5. 验证新密码是否和原密码相同
        if new_password == old_password:
            messages.error(request, '新密码不能和原密码相同！')
            return render(request, 'user/change_password.html')
        
        # 6. 所有校验通过，更新密码
        request.user.set_password(new_password)
        request.user.save()
        
        # 关键：保持用户登录状态（否则改密后会自动登出）
        update_session_auth_hash(request, request.user)
        
        messages.success(request, '密码修改成功！')
        return redirect('user_profile')  # 改密成功后返回个人信息页
    
    # GET请求：显示改密页面
    return render(request, 'user/change_password.html')


# ---------------------- 普通用户视图 ----------------------
def user_home(request):
    return render(request, 'user/home.html')

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
def teacher_approve(request):
    """指导教师审批视图"""
    user_info = get_object_or_404(UserInfo, auth_user=request.user)
    
    # 安全校验：确保只有教师能进入
    if user_info.user_type != 'teacher':
        messages.error(request, '只有教师账号可以访问审批页面！')
        return redirect('user_home')

    # 获取分配给该教师审批的预约（通过 teacher_id 匹配）
    bookings = Booking.objects.filter(
        status='teacher_pending',
        teacher_id=user_info.user_code
    ).order_by('-create_time')

    if request.method == 'POST':
        booking_id = request.POST.get('booking_id')
        action = request.POST.get('action') # 'approve' 或 'reject'
        booking = get_object_or_404(Booking, id=booking_id)

        if action == 'approve':
            booking.status = 'pending'  # 流转给管理员
            msg = "批准"
        else:
            booking.status = 'teacher_rejected'
            msg = "拒绝"
        
        booking.save()
        
        # 记录审批日志
        ApprovalRecord.objects.create(
            booking=booking,
            approver=request.user,
            approval_level='teacher',
            action=action,
            comment=request.POST.get('comment', '')
        )
        
        messages.success(request, f'已成功{msg}学生 {booking.applicant.name} 的预约。')
        return redirect('teacher_approve')

    return render(request, 'user/teacher_approve.html', {'bookings': bookings})