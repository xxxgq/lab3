from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.contrib.auth.hashers import make_password
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages

# 导入业务模型
from user.models import UserInfo
from devices.models import Device
from booking.models import Booking, ApprovalRecord
# 导入所有表单
from .forms import UserInfoForm, RegistrationForm, StudentForm, StudentIdForm

# ---------------------- 基础用户视图 ----------------------

@login_required
def user_profile(request):
    """个人信息管理视图"""
    try:
        user_info = UserInfo.objects.get(auth_user=request.user)
    except UserInfo.DoesNotExist:
        messages.error(request, '未找到你的个人信息，请联系管理员！')
        return redirect('user_home')
    
    # 教师用户：获取指导的学生列表（整合他人精确匹配逻辑）
    advisor_students = []
    if user_info.user_type == 'teacher':
        advisor_students = UserInfo.objects.filter(
            user_type='student', 
            advisor__icontains=user_info.name  
        )
    
    if request.method == 'POST':
        # 更新基础信息
        user_info.name = request.POST.get('name')
        user_info.gender = request.POST.get('gender')
        user_info.department = request.POST.get('department')
        user_info.phone = request.POST.get('phone')
        
        # 更新专属字段
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
    
    context = {
        'user_info': user_info,
        'advisor_students': advisor_students
    }
    return render(request, 'user/user_profile.html', context)

@login_required
def change_password(request):
    """修改密码视图"""
    if request.method == 'POST':
        old_password = request.POST.get('old_password', '').strip()
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        
        if not old_password or not new_password or not confirm_password:
            messages.error(request, '请填写所有密码字段！')
            return render(request, 'user/change_password.html')
        
        if not request.user.check_password(old_password):
            messages.error(request, '原密码输入错误，请重新输入！')
            return render(request, 'user/change_password.html')
        
        if new_password != confirm_password:
            messages.error(request, '两次输入的新密码不一致！')
            return render(request, 'user/change_password.html')
        
        if new_password == old_password:
            messages.error(request, '新密码不能和原密码相同！')
            return render(request, 'user/change_password.html')
        
        request.user.set_password(new_password)
        request.user.save()
        update_session_auth_hash(request, request.user)
        messages.success(request, '密码修改成功！')
        return redirect('user_profile')
    
    return render(request, 'user/change_password.html')

def user_home(request):
    return render(request, 'user/home.html')

def device_list(request):
    """用户端设备查询视图"""
    keyword = request.GET.get('keyword', '')
    devices = Device.objects.all().order_by('device_code')
    if keyword:
        devices = devices.filter(
            Q(device_code__icontains=keyword) | 
            Q(model__icontains=keyword) |
            Q(manufacturer__icontains=keyword) |
            Q(purpose__icontains=keyword)
        )
    return render(request, 'user/device_list.html', {'devices': devices, 'keyword': keyword})

# ---------------------- 您的核心功能：教师审批 ----------------------

@login_required
def teacher_approve(request):
    """指导教师审批视图（保留您的核心逻辑）"""
    user_info = get_object_or_404(UserInfo, auth_user=request.user)
    
    if user_info.user_type != 'teacher':
        messages.error(request, '只有教师账号可以访问审批页面！')
        return redirect('user_home')

    # 获取分配给该教师审批的预约
    bookings = Booking.objects.filter(
        status='teacher_pending',
        teacher_id=user_info.user_code
    ).order_by('-create_time')

    if request.method == 'POST':
        booking_id = request.POST.get('booking_id')
        action = request.POST.get('action') 
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

# ---------------------- 他人新增功能：注册与学生管理 ----------------------

def register_view(request):
    """用户注册视图"""
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user_code = form.cleaned_data['user_code']
            password = form.cleaned_data['password']
            name = form.cleaned_data['name']
            
            try:
                # 1. 创建登录账号
                user = User.objects.create_user(
                    username=user_code,
                    password=password,
                    first_name=name,
                    is_active=True
                )
                # 2. 创建扩展信息
                user_info = form.save(commit=False)
                user_info.auth_user = user
                user_info.save()
                
                messages.success(request, f'注册成功！请使用编号 {user_code} 登录')
                return redirect('user_login')
            except Exception as e:
                messages.error(request, f'注册失败：{str(e)}')
    else:
        form = RegistrationForm()
    return render(request, 'user/register.html', {'form': form})

def teacher_required(function=None):
    """教师权限检查装饰器"""
    actual_decorator = user_passes_test(
        lambda u: hasattr(u, 'userinfo') and u.userinfo.user_type == 'teacher',
        login_url='user_profile',
        redirect_field_name=None
    )
    if function: return actual_decorator(function)
    return actual_decorator

@login_required
@teacher_required
def add_student(request):
    """教师添加学生 - 第一步：查验学号"""
    teacher_info = UserInfo.objects.get(auth_user=request.user)
    if request.method == 'POST':
        form = StudentIdForm(request.POST)
        if form.is_valid():
            user_code = form.cleaned_data['user_code']
            try:
                existing_student = UserInfo.objects.get(user_code=user_code)
                if existing_student.user_type == 'student':
                    existing_student.advisor = teacher_info.name
                    existing_student.save()
                    messages.success(request, f'学生 {existing_student.name} 已存在，成功添加关联！')
                    return redirect('user_profile')
                else:
                    messages.error(request, f'编号 {user_code} 不是学生类型！')
            except UserInfo.DoesNotExist:
                request.session['adding_student_code'] = user_code
                return redirect('add_student_full')
    else:
        form = StudentIdForm()
    return render(request, 'user/add_student_step1.html', {'form': form, 'teacher_info': teacher_info})

@login_required
@teacher_required
def add_student_full(request):
    """教师添加学生 - 第二步：完整注册"""
    teacher_info = UserInfo.objects.get(auth_user=request.user)
    user_code = request.session.get('adding_student_code')
    if not user_code: return redirect('add_student')
    
    if request.method == 'POST':
        form = StudentForm(request.POST, teacher_name=teacher_info.name)
        if form.is_valid():
            try:
                user = User.objects.create_user(
                    username=user_code, password=user_code,
                    first_name=form.cleaned_data['name'], is_active=True
                )
                student = form.save(commit=False)
                student.user_code, student.auth_user, student.user_type = user_code, user, 'student'
                student.save()
                del request.session['adding_student_code']
                messages.success(request, f'已注册并关联学生 {student.name}！')
                return redirect('user_profile')
            except Exception as e:
                messages.error(request, f'添加失败：{str(e)}')
    else:
        form = StudentForm(teacher_name=teacher_info.name)
        form.fields['user_code'].initial = user_code
    return render(request, 'user/add_student_step2.html', {'form': form, 'user_code': user_code})

@login_required
@teacher_required
def edit_student(request, student_id):
    """教师编辑学生信息"""
    teacher_info = UserInfo.objects.get(auth_user=request.user)
    student = get_object_or_404(UserInfo, id=student_id, advisor=teacher_info.name)
    
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student, teacher_name=teacher_info.name)
        if form.is_valid():
            form.save()
            if student.auth_user:
                student.auth_user.first_name = form.cleaned_data['name']
                student.auth_user.save()
            messages.success(request, '学生信息更新成功！')
            return redirect('user_profile')
    else:
        form = StudentForm(instance=student, teacher_name=teacher_info.name)
    return render(request, 'user/student_form.html', {'form': form, 'student': student})

@login_required
@teacher_required
def remove_student(request, student_id):
    """教师解绑指导学生"""
    teacher_info = UserInfo.objects.get(auth_user=request.user)
    student = get_object_or_404(UserInfo, id=student_id, advisor=teacher_info.name)
    if request.method == 'POST':
        student.advisor = ''
        student.save()
        messages.success(request, f'已移除学生 {student.name} 的指导关系')
    return redirect('user_profile')