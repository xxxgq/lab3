from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.http import HttpResponse
from django.db.models import Q, Count
import csv
from .models import DeviceLedger
from devices.models import Device, DEVICE_STATUS
from user.models import UserInfo
from booking.models import Booking

def check_ledger_permission(view_func):
    """权限检查装饰器：只允许设备管理员和实验室负责人访问台账"""
    def wrapper(request, *args, **kwargs):
        is_admin = request.user.groups.filter(name='设备管理员').exists()
        is_manager = request.user.groups.filter(name='实验室负责人').exists()
        if not is_admin and not is_manager:
            messages.error(request, '您无权访问台账模块！')
            # 尝试重定向到管理员首页，如果不存在则重定向到登录页
            try:
                return redirect('admin_home')
            except:
                return redirect('user_login')
        return view_func(request, *args, **kwargs)
    return wrapper

@login_required
@check_ledger_permission
def ledger_home(request):
    """台账选择页面"""
    is_admin = request.user.groups.filter(name='设备管理员').exists()
    is_manager = request.user.groups.filter(name='实验室负责人').exists()
    context = {
        'is_admin': is_admin,
        'is_manager': is_manager,
    }
    return render(request, 'ledger/ledger_home.html', context)

def get_user_role_context(request):
    """辅助函数：获取用户角色信息"""
    is_admin = request.user.groups.filter(name='设备管理员').exists()
    is_manager = request.user.groups.filter(name='实验室负责人').exists()
    return {
        'is_admin': is_admin,
        'is_manager': is_manager,
    }

@login_required
@check_ledger_permission
def device_ledger_list(request):
    """设备台账列表视图：显示所有设备信息"""
    devices = Device.objects.all().order_by('device_code')

    # 筛选
    device_code = request.GET.get('device_code')
    if device_code:
        devices = devices.filter(device_code__icontains=device_code)

    model = request.GET.get('model')
    if model:
        devices = devices.filter(model__icontains=model)

    manufacturer = request.GET.get('manufacturer')
    if manufacturer:
        devices = devices.filter(manufacturer__icontains=manufacturer)

    status = request.GET.get('status')
    if status:
        devices = devices.filter(status=status)

    # 分页
    paginator = Paginator(devices, 20)  # 每页20条记录
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'status_choices': DEVICE_STATUS,
        'total_count': devices.count(),
    }
    context.update(get_user_role_context(request))
    return render(request, 'ledger/device_info_ledger_list.html', context)

@login_required
@check_ledger_permission
def device_operation_history_list(request):
    """设备操作历史列表视图（保留原有功能）"""
    ledgers = DeviceLedger.objects.select_related('device', 'user', 'operator').order_by('-operation_date')

    # 筛选
    device_code = request.GET.get('device_code')
    if device_code:
        ledgers = ledgers.filter(device__device_code__icontains=device_code)

    operation_type = request.GET.get('operation_type')
    if operation_type:
        ledgers = ledgers.filter(operation_type=operation_type)

    date_from = request.GET.get('date_from')
    if date_from:
        ledgers = ledgers.filter(operation_date__date__gte=date_from)

    date_to = request.GET.get('date_to')
    if date_to:
        ledgers = ledgers.filter(operation_date__date__lte=date_to)

    operator_name = request.GET.get('operator')
    if operator_name:
        ledgers = ledgers.filter(operator__username__icontains=operator_name)

    # 分页
    paginator = Paginator(ledgers, 20)  # 每页20条记录
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'operation_types': DeviceLedger.OPERATION_TYPES,
        'total_count': ledgers.count(),
    }
    return render(request, 'ledger/device_ledger_list.html', context)

@login_required
@check_ledger_permission
def teacher_ledger_list(request):
    """教师台账列表视图：显示申请过设备借用的教师信息"""
    # 筛选出申请过设备借用的教师（通过Booking关联），预加载设备信息
    teachers = UserInfo.objects.filter(
        user_type='teacher',
        booking__isnull=False
    ).distinct().prefetch_related('booking_set__device').annotate(
        booking_count=Count('booking')
    ).order_by('user_code')

    # 筛选
    user_code = request.GET.get('user_code')
    if user_code:
        teachers = teachers.filter(user_code__icontains=user_code)

    name = request.GET.get('name')
    if name:
        teachers = teachers.filter(name__icontains=name)

    department = request.GET.get('department')
    if department:
        teachers = teachers.filter(department__icontains=department)

    title = request.GET.get('title')
    if title:
        teachers = teachers.filter(title__icontains=title)

    # 分页
    paginator = Paginator(teachers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'total_count': teachers.count(),
    }
    context.update(get_user_role_context(request))
    return render(request, 'ledger/teacher_ledger_list.html', context)

@login_required
@check_ledger_permission
def student_ledger_list(request):
    """学生台账列表视图：显示申请过设备借用的学生信息"""
    # 筛选出申请过设备借用的学生（通过Booking关联），预加载设备信息
    students = UserInfo.objects.filter(
        user_type='student',
        booking__isnull=False
    ).distinct().prefetch_related('booking_set__device').annotate(
        booking_count=Count('booking')
    ).order_by('user_code')

    # 筛选
    user_code = request.GET.get('user_code')
    if user_code:
        students = students.filter(user_code__icontains=user_code)

    name = request.GET.get('name')
    if name:
        students = students.filter(name__icontains=name)

    department = request.GET.get('department')
    if department:
        students = students.filter(department__icontains=department)

    major = request.GET.get('major')
    if major:
        students = students.filter(major__icontains=major)

    advisor = request.GET.get('advisor')
    if advisor:
        students = students.filter(advisor__icontains=advisor)

    # 分页
    paginator = Paginator(students, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'total_count': students.count(),
    }
    context.update(get_user_role_context(request))
    return render(request, 'ledger/student_ledger_list.html', context)

@login_required
@check_ledger_permission
def external_ledger_list(request):
    """校外人员台账列表视图：显示申请过设备借用的校外人员信息"""
    # 筛选出申请过设备借用的校外人员（通过Booking关联），预加载设备信息
    externals = UserInfo.objects.filter(
        user_type='external',
        booking__isnull=False
    ).distinct().prefetch_related('booking_set__device').annotate(
        booking_count=Count('booking')
    ).order_by('user_code')

    # 筛选
    user_code = request.GET.get('user_code')
    if user_code:
        externals = externals.filter(user_code__icontains=user_code)

    name = request.GET.get('name')
    if name:
        externals = externals.filter(name__icontains=name)

    department = request.GET.get('department')
    if department:
        externals = externals.filter(department__icontains=department)

    # 分页
    paginator = Paginator(externals, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'total_count': externals.count(),
    }
    context.update(get_user_role_context(request))
    return render(request, 'ledger/external_ledger_list.html', context)

@login_required
@check_ledger_permission
def booking_ledger_list(request):
    """预约台账列表视图：显示所有预约申请信息"""
    bookings = Booking.objects.select_related('applicant', 'device').order_by('-create_time')

    # 筛选
    booking_code = request.GET.get('booking_code')
    if booking_code:
        bookings = bookings.filter(booking_code__icontains=booking_code)

    device_code = request.GET.get('device_code')
    if device_code:
        bookings = bookings.filter(device__device_code__icontains=device_code)

    applicant_name = request.GET.get('applicant_name')
    if applicant_name:
        bookings = bookings.filter(applicant__name__icontains=applicant_name)

    user_type = request.GET.get('user_type')
    if user_type:
        bookings = bookings.filter(applicant__user_type=user_type)

    status = request.GET.get('status')
    if status:
        bookings = bookings.filter(status=status)

    date_from = request.GET.get('date_from')
    if date_from:
        bookings = bookings.filter(booking_date__gte=date_from)

    date_to = request.GET.get('date_to')
    if date_to:
        bookings = bookings.filter(booking_date__lte=date_to)

    # 分页
    paginator = Paginator(bookings, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'status_choices': Booking.APPROVAL_STATUS,
        'user_type_choices': UserInfo.USER_TYPE_CHOICES,
        'total_count': bookings.count(),
    }
    context.update(get_user_role_context(request))
    return render(request, 'ledger/booking_ledger_list.html', context)

@login_required
def device_ledger_detail(request, pk):
    """设备台账详情视图"""
    ledger = get_object_or_404(DeviceLedger, pk=pk)
    return render(request, 'ledger/device_ledger_detail.html', {'ledger': ledger})

@login_required
@check_ledger_permission
def export_device_ledger_csv(request):
    """导出设备台账为CSV文件"""
    devices = Device.objects.all().order_by('device_code')

    # 应用相同的筛选条件
    device_code = request.GET.get('device_code')
    if device_code:
        devices = devices.filter(device_code__icontains=device_code)

    model = request.GET.get('model')
    if model:
        devices = devices.filter(model__icontains=model)

    manufacturer = request.GET.get('manufacturer')
    if manufacturer:
        devices = devices.filter(manufacturer__icontains=manufacturer)

    status = request.GET.get('status')
    if status:
        devices = devices.filter(status=status)

    # 创建CSV响应
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="device_info_ledger.csv"'

    # 添加BOM以支持中文
    response.write('\ufeff'.encode('utf-8'))

    writer = csv.writer(response)
    writer.writerow([
        '设备编号', '型号', '购入时间', '生产厂商', '实验用途', 
        '时段可用状态', '校内租用价格（元/2小时）', '校外租用价格（元/2小时）', '创建时间', '更新时间'
    ])

    for device in devices:
        writer.writerow([
            device.device_code,
            device.model,
            device.purchase_date.strftime('%Y-%m-%d') if device.purchase_date else '-',
            device.manufacturer,
            device.purpose or '-',
            device.get_status_display(),
            str(device.price_internal),
            str(device.price_external),
            device.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            device.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
        ])

    return response

@login_required
@check_ledger_permission
def export_teacher_ledger_csv(request):
    """导出教师台账为CSV文件"""
    teachers = UserInfo.objects.filter(
        user_type='teacher',
        booking__isnull=False
    ).distinct().prefetch_related('booking_set__device').annotate(
        booking_count=Count('booking')
    ).order_by('user_code')

    # 应用相同的筛选条件
    user_code = request.GET.get('user_code')
    if user_code:
        teachers = teachers.filter(user_code__icontains=user_code)

    name = request.GET.get('name')
    if name:
        teachers = teachers.filter(name__icontains=name)

    department = request.GET.get('department')
    if department:
        teachers = teachers.filter(department__icontains=department)

    title = request.GET.get('title')
    if title:
        teachers = teachers.filter(title__icontains=title)

    # 创建CSV响应
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="teacher_ledger.csv"'

    # 添加BOM以支持中文
    response.write('\ufeff'.encode('utf-8'))

    writer = csv.writer(response)
    writer.writerow([
        '教师编号', '姓名', '性别', '职称', '专业方向', '所在学院', '联系电话', '借用设备', '创建时间'
    ])

    for teacher in teachers:
        # 获取所有借用的设备编号，多次借用就记录多次
        device_codes = [booking.device.device_code for booking in teacher.booking_set.all()]
        device_str = '、'.join(device_codes) if device_codes else '-'
        writer.writerow([
            teacher.user_code,
            teacher.name,
            teacher.gender,
            teacher.title or '-',
            teacher.research_field or '-',
            teacher.department,
            teacher.phone,
            device_str,
            teacher.create_time.strftime('%Y-%m-%d %H:%M:%S'),
        ])

    return response

@login_required
@check_ledger_permission
def export_student_ledger_csv(request):
    """导出学生台账为CSV文件"""
    students = UserInfo.objects.filter(
        user_type='student',
        booking__isnull=False
    ).distinct().prefetch_related('booking_set__device').annotate(
        booking_count=Count('booking')
    ).order_by('user_code')

    # 应用相同的筛选条件
    user_code = request.GET.get('user_code')
    if user_code:
        students = students.filter(user_code__icontains=user_code)

    name = request.GET.get('name')
    if name:
        students = students.filter(name__icontains=name)

    department = request.GET.get('department')
    if department:
        students = students.filter(department__icontains=department)

    major = request.GET.get('major')
    if major:
        students = students.filter(major__icontains=major)

    advisor = request.GET.get('advisor')
    if advisor:
        students = students.filter(advisor__icontains=advisor)

    # 创建CSV响应
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="student_ledger.csv"'

    # 添加BOM以支持中文
    response.write('\ufeff'.encode('utf-8'))

    writer = csv.writer(response)
    writer.writerow([
        '学号', '姓名', '性别', '专业', '导师', '所在学院', '联系电话', '借用设备', '创建时间'
    ])

    for student in students:
        # 获取所有借用的设备编号，多次借用就记录多次
        device_codes = [booking.device.device_code for booking in student.booking_set.all()]
        device_str = '、'.join(device_codes) if device_codes else '-'
        writer.writerow([
            student.user_code,
            student.name,
            student.gender,
            student.major or '-',
            student.advisor or '-',
            student.department,
            student.phone,
            device_str,
            student.create_time.strftime('%Y-%m-%d %H:%M:%S'),
        ])

    return response

@login_required
@check_ledger_permission
def export_external_ledger_csv(request):
    """导出校外人员台账为CSV文件"""
    externals = UserInfo.objects.filter(
        user_type='external',
        booking__isnull=False
    ).distinct().prefetch_related('booking_set__device').annotate(
        booking_count=Count('booking')
    ).order_by('user_code')

    # 应用相同的筛选条件
    user_code = request.GET.get('user_code')
    if user_code:
        externals = externals.filter(user_code__icontains=user_code)

    name = request.GET.get('name')
    if name:
        externals = externals.filter(name__icontains=name)

    department = request.GET.get('department')
    if department:
        externals = externals.filter(department__icontains=department)

    # 创建CSV响应
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="external_ledger.csv"'

    # 添加BOM以支持中文
    response.write('\ufeff'.encode('utf-8'))

    writer = csv.writer(response)
    writer.writerow([
        '编号', '姓名', '性别', '所在单位名称', '联系电话', '借用设备', '创建时间'
    ])

    for external in externals:
        # 获取所有借用的设备编号，多次借用就记录多次
        device_codes = [booking.device.device_code for booking in external.booking_set.all()]
        device_str = '、'.join(device_codes) if device_codes else '-'
        writer.writerow([
            external.user_code,
            external.name,
            external.gender,
            external.department,
            external.phone,
            device_str,
            external.create_time.strftime('%Y-%m-%d %H:%M:%S'),
        ])

    return response

@login_required
@check_ledger_permission
def export_booking_ledger_csv(request):
    """导出预约台账为CSV文件"""
    bookings = Booking.objects.select_related('applicant', 'device').order_by('-create_time')

    # 应用相同的筛选条件
    booking_code = request.GET.get('booking_code')
    if booking_code:
        bookings = bookings.filter(booking_code__icontains=booking_code)

    device_code = request.GET.get('device_code')
    if device_code:
        bookings = bookings.filter(device__device_code__icontains=device_code)

    applicant_name = request.GET.get('applicant_name')
    if applicant_name:
        bookings = bookings.filter(applicant__name__icontains=applicant_name)

    user_type = request.GET.get('user_type')
    if user_type:
        bookings = bookings.filter(applicant__user_type=user_type)

    status = request.GET.get('status')
    if status:
        bookings = bookings.filter(status=status)

    date_from = request.GET.get('date_from')
    if date_from:
        bookings = bookings.filter(booking_date__gte=date_from)

    date_to = request.GET.get('date_to')
    if date_to:
        bookings = bookings.filter(booking_date__lte=date_to)

    # 创建CSV响应
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="booking_ledger.csv"'

    # 添加BOM以支持中文
    response.write('\ufeff'.encode('utf-8'))

    writer = csv.writer(response)
    writer.writerow([
        '预约编号', '申请人编号', '申请人姓名', '申请人类型', '设备编号', '设备型号',
        '预约日期', '预约时段', '借用用途', '指导教师编号', '审批状态', '创建时间', '更新时间'
    ])

    for booking in bookings:
        writer.writerow([
            booking.booking_code,
            booking.applicant.user_code,
            booking.applicant.name,
            booking.applicant.get_user_type_display(),
            booking.device.device_code,
            booking.device.model,
            booking.booking_date.strftime('%Y-%m-%d'),
            booking.time_slot,
            booking.purpose or '-',
            booking.teacher_id or '-',
            booking.get_status_display(),
            booking.create_time.strftime('%Y-%m-%d %H:%M:%S'),
            booking.update_time.strftime('%Y-%m-%d %H:%M:%S'),
        ])

    return response

@login_required
def export_ledger_csv(request):
    """导出设备操作历史为CSV文件（保留原有功能）"""
    ledgers = DeviceLedger.objects.select_related('device', 'user', 'operator').order_by('-operation_date')

    # 应用相同的筛选条件
    device_code = request.GET.get('device_code')
    if device_code:
        ledgers = ledgers.filter(device__device_code__icontains=device_code)

    operation_type = request.GET.get('operation_type')
    if operation_type:
        ledgers = ledgers.filter(operation_type=operation_type)

    date_from = request.GET.get('date_from')
    if date_from:
        ledgers = ledgers.filter(operation_date__date__gte=date_from)

    date_to = request.GET.get('date_to')
    if date_to:
        ledgers = ledgers.filter(operation_date__date__lte=date_to)

    operator_name = request.GET.get('operator')
    if operator_name:
        ledgers = ledgers.filter(operator__username__icontains=operator_name)

    # 创建CSV响应
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="device_operation_history.csv"'

    # 添加BOM以支持中文
    response.write('\ufeff'.encode('utf-8'))

    writer = csv.writer(response)
    writer.writerow([
        '设备编号', '设备名称', '借用人', '操作类型', '操作日期',
        '预期归还时间', '实际归还时间', '设备状态', '操作员', '备注'
    ])

    for ledger in ledgers:
        # 处理设备编号：优先使用device.device_code，否则从description中提取
        if ledger.device:
            device_code = ledger.device.device_code
        elif ledger.operation_type == 'discard' and '删除设备：' in (ledger.description or ''):
            # 从删除描述中提取设备编号
            desc = ledger.description or ''
            if '删除设备：' in desc:
                device_code = desc.split('删除设备：')[1].split(' - ')[0]
            else:
                device_code = ledger.device_name
        else:
            device_code = ledger.device_name
        
        writer.writerow([
            device_code,
            ledger.device_name,
            ledger.user.name if ledger.user else '',
            ledger.get_operation_type_display(),
            ledger.operation_date.strftime('%Y-%m-%d %H:%M:%S'),
            ledger.expected_return_date.strftime('%Y-%m-%d %H:%M:%S') if ledger.expected_return_date else '-',
            ledger.actual_return_date.strftime('%Y-%m-%d %H:%M:%S') if ledger.actual_return_date else '-',
            ledger.get_status_after_operation_display(),
            ledger.operator.username if ledger.operator else '系统',
            ledger.description or ''
        ])

    return response