from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from user.models import UserInfo
from devices.models import Device
from .models import Booking, ApprovalRecord  # 👈 在这里加上 ApprovalRecord
from .utils import generate_booking_code
from django.http import JsonResponse
from django.urls import reverse

# 1. 设备预约申请页面
@login_required
def booking_apply(request):
    """设备预约申请视图"""
    # 获取当前登录用户的信息
    try:
        user_info = UserInfo.objects.get(auth_user=request.user)
    except UserInfo.DoesNotExist:
        messages.error(request, '未找到你的个人信息，请联系管理员！')
        return redirect('user_home')
    
    # 获取所有可用设备
    devices = Device.objects.filter(status='可用')
    
    if request.method == 'POST':
        # 获取表单数据
        device_code = request.POST.get('device_id')
        booking_date = request.POST.get('booking_date')
        time_slot = request.POST.get('time_slot')
        purpose = request.POST.get('purpose')
        teacher_id = request.POST.get('teacher_id', '')
        
        # 校验设备是否存在且可用
        try:
            device = Device.objects.get(device_code=device_code, status='可用')
        except Device.DoesNotExist:
            messages.error(request, '该设备不存在或不可用！')
            return render(request, 'users/booking_apply.html', {
                'user_info': user_info,
                'devices': devices
            })
        
        # 学生用户必须填写指导教师
        if user_info.user_type == 'student' and not teacher_id:
            messages.error(request, '学生用户必须填写指导教师编号！')
            return render(request, 'users/booking_apply.html', {
                'user_info': user_info,
                'devices': devices
            })
        
        # 生成预约编号
        booking_code = generate_booking_code()
        if user_info.user_type == 'student':
            initial_status = 'teacher_pending'  # 学生申请，进入教师审批流程
        else:
            initial_status = 'pending'
        # 创建预约申请
        Booking.objects.create(
            booking_code=booking_code,
            applicant=user_info,
            device=device,
            booking_date=booking_date,
            time_slot=time_slot,
            purpose=purpose,
            teacher_id=teacher_id,
            # 校外人员默认待管理员审批，审批通过后需负责人审批
            status=initial_status
        )
        if initial_status == 'teacher_pending':
            msg = f"预约提交成功！编号：{booking_code}，请提醒指导教师（编号：{teacher_id}）进行首轮审批。"
        else:
            msg = f"预约提交成功！编号：{booking_code}，请等待管理员审批。"
        messages.success(request, msg)
        return redirect('my_booking')
    
    # GET请求：渲染申请页面
    context = {
        'user_info': user_info,
        'devices': devices
    }
    print(context['devices'])
    return render(request, 'user/booking_apply.html', context)

# 2. 我的预约记录页面
@login_required
def my_booking(request):
    """我的预约记录页面"""
    # 获取当前用户信息
    try:
        user_info = UserInfo.objects.get(auth_user=request.user)
    except UserInfo.DoesNotExist:
        messages.error(request, '未找到你的个人信息，请联系管理员！')
        return redirect('user_home')
    
    # 状态筛选（全部/待审批/已批准/已拒绝/已撤销）
    status_filter = request.GET.get('status', 'all')
    bookings = Booking.objects.filter(applicant=user_info).order_by('-create_time')
    
    # 筛选状态
    if status_filter != 'all' and status_filter in [s[0] for s in Booking.APPROVAL_STATUS]:
        bookings = bookings.filter(status=status_filter)
    
    context = {
        'bookings': bookings,
        'status_filter': status_filter,
        'APPROVAL_STATUS': Booking.APPROVAL_STATUS
    }
    return render(request, 'user/my_booking.html', context)

# 3. 撤销预约申请
@login_required
def cancel_booking(request, booking_id):
    """撤销预约申请"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    # 校验是否是本人的预约
    try:
        user_info = UserInfo.objects.get(auth_user=request.user)
        if booking.applicant != user_info:
            messages.error(request, '你无权撤销他人的预约申请！')
            return redirect('my_booking')
    except UserInfo.DoesNotExist:
        messages.error(request, '未找到你的个人信息，请联系管理员！')
        return redirect('my_booking')
    
    # 只能撤销待审批的申请
    if booking.status not in ['pending', 'admin_approved']:
        messages.error(request, '该申请已审批完成，无法撤销！')
        return redirect('my_booking')
    
    # 更新状态为已撤销
    booking.status = 'cancelled'
    booking.save()
    
    messages.success(request, '预约申请已成功撤销！')
    return redirect('my_booking')
def device_booking_detail(request, device_id):
    """设备预约详情页面"""
    # 获取设备信息，不存在则返回404
    device = get_object_or_404(Device, id=device_id)
    # 查询该设备的所有预约记录（按预约时间倒序）
    bookings = Booking.objects.filter(device=device).order_by('-create_time')
    
    context = {
        'device': device,
        'bookings': bookings
    }
    return render(request, 'user/device_booking_detail.html', context)
def check_availability(request):
    """检查设备在指定日期和时段是否空闲"""
    device_id = request.GET.get('device_id')
    booking_date = request.GET.get('date')
    time_slot = request.GET.get('time_slot')

    # 验证参数
    if not all([device_id, booking_date, time_slot]):
        return JsonResponse({
            'available': False,
            'reason': '参数不完整'
        })

    # 检查设备是否存在
    try:
        device = Device.objects.get(device_code=device_id)  # 注意匹配设备编号字段
    except Device.DoesNotExist:
        return JsonResponse({
            'available': False,
            'reason': '设备不存在'
        })

    # 检查该时段是否已有预约
    existing_booking = Booking.objects.filter(
        device__device_code=device_id,  # 关联设备
        booking_date=booking_date,      # 预约日期
        time_slot=time_slot,            # 预约时段
        status__in=['pending', 'approved']  # 待审核或已通过的预约视为占用
    ).exists()

    if existing_booking:
        return JsonResponse({
            'available': False,
            'reason': '已有其他预约'
        })
    else:
        return JsonResponse({'available': True})
