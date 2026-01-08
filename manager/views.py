from django.shortcuts import render, redirect, get_object_or_404

from django.db.models import Q
from user.models import UserInfo
from user.forms import UserInfoForm
from django.contrib.auth.hashers import make_password  # 密码加密

# 以下是创建角色组和初始用户的代码
from django.contrib.auth.models import User, Group, Permission

from django.contrib.auth.decorators import login_required
from user.models import UserInfo
from booking.models import Booking, ApprovalRecord
from django.contrib import messages

from labadmin.views import handle_approval

# Create your views here.
# ---------------------- 负责人视图 ----------------------
def manager_home(request):
    return render(request, 'manager/home.html')

@login_required
def booking_approve(request):
    """设备预约审批（管理员/负责人）"""
    # 校验是否是管理员/负责人
    is_admin = request.user.groups.filter(name='设备管理员').exists()
    is_manager = request.user.groups.filter(name='实验室负责人').exists()
    if not is_admin and not is_manager:
        messages.error(request, '你无审批权限！')
        return redirect('manager_home')
    
    # 获取筛选条件
    user_type_filter = request.GET.get('user_type', 'all')
    
    # ========== 核心修改：精准限定各角色的查询范围 ==========
    if is_admin:
        # 管理员：只看「待管理员审批（pending）」的申请（已批准的不再显示）
        bookings = Booking.objects.filter(
            status='pending'  # 仅待管理员审批
        ).order_by('-create_time')
    else:  # 实验室负责人
        # 负责人：只看「管理员已批准（admin_approved）」的申请（且仅校外人员）
        bookings = Booking.objects.filter(
            status='admin_approved',  # 仅管理员已批准的
            applicant__user_type='external'  # 仅校外人员（符合原有业务规则）
        ).order_by('-create_time')
    
    # 筛选用户类型（仅对管理员生效，负责人默认只看校外人员，筛选不影响）
    if user_type_filter != 'all':
        if is_admin:  # 管理员可筛选所有类型
            bookings = bookings.filter(applicant__user_type=user_type_filter)
        # 负责人：强制限定为校外人员，忽略其他筛选（避免误看非校外人员申请）
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
    return render(request, 'manager/booking_approve.html', context)

def manager_report_stat(request):
    return render(request, 'manager/report_stat.html')

# -----------------------s--- 1. 用户列表（含搜索、筛选） --------------------------
def user_manage(request):
    """
    用户管理主页面：展示所有用户，支持按姓名/编号搜索、按类型筛选
    对应路径：/manager/user/manage/
    """
    # 1. 处理筛选和搜索（原有逻辑不变）
    user_type = request.GET.get('user_type', '')
    keyword = request.GET.get('keyword', '')
    user = UserInfo.objects.all()
    if user_type and user_type in ['student', 'teacher', 'external']:
        user = user.filter(user_type=user_type)
    if keyword:
        user = user.filter(Q(name__icontains=keyword) | Q(user_code__icontains=keyword))
    
    # 2. 处理新增用户（POST请求）【核心修改：用户名=用户编号，密码=用户编号】
    if request.method == 'POST':
        form = UserInfoForm(request.POST)
        if form.is_valid():
            # 先保存UserInfo（不提交到数据库）
            user_info = form.save(commit=False)
            
            # 【关键修改】用户名 = 用户编号（学号/工号），密码 = 用户编号
            username = user_info.user_code  # 账号用编号（如20230001/T001/O001）
            password = make_password(user_info.user_code)  # 密码用编号（加密）
            
            # 检查用户名是否已存在（用户编号本身已设置unique=True，此处双重保险）
            if User.objects.filter(username=username).exists():
                # 理论上不会触发，因为user_code是唯一的
                form.add_error('user_code', '该用户编号已作为登录账号存在！')
                return render(request, 'manager/user_manage.html', {
                    'user': user,
                    'keyword': keyword,
                    'user_type': user_type,
                    'form': form,
                })
            
            # 创建登录账号
            auth_user = User.objects.create(
                username=username,          # 账号=用户编号
                password=password,          # 密码=用户编号（加密）
                first_name=user_info.name,  # 姓名（可选）
                is_active=user_info.is_active  # 借用资格=账号是否激活
            )
            
            # 关联登录账号到UserInfo，并加入普通用户组
            user_info.auth_user = auth_user
            user_info.save()
            
            # 可选：将普通用户加入「普通用户」组
            user_group = Group.objects.get(name='普通用户')
            auth_user.groups.add(user_group)
            auth_user.save()
            
            return redirect('user_manage')
    else:
        form = UserInfoForm()
    
    # 3. 准备上下文（原有逻辑不变）
    context = {
        'users': user,
        'keyword': keyword,
        'user_type': user_type,
        'form': form,
    }
    return render(request, 'manager/user_manage.html', context)

# -------------------------- 2. 编辑用户 --------------------------
def user_edit(request, pk):
    """编辑用户信息"""
    user_info = get_object_or_404(UserInfo, pk=pk)
    
    if request.method == 'POST':
        form = UserInfoForm(request.POST, instance=user_info)
        if form.is_valid():
            user_info = form.save(commit=False)
            
            # 【关键】如果修改了用户编号，同步更新登录账号的用户名
            if user_info.auth_user and user_info.auth_user.username != user_info.user_code:
                user_info.auth_user.username = user_info.user_code
                user_info.auth_user.save()
            
            # 同步更新登录账号激活状态
            if user_info.auth_user:
                user_info.auth_user.is_active = user_info.is_active
                
                # 可选：如果表单填写了「重置密码为编号」，则更新密码
                reset_to_code = request.POST.get('reset_to_code', '')
                if reset_to_code:
                    user_info.auth_user.password = make_password(user_info.user_code)
                
                user_info.auth_user.save()
            
            user_info.save()
            return redirect('user_manage')
    else:
        form = UserInfoForm(instance=user_info)
    
    context = {
        'form': form,
        'user': user_info,
    }
    return render(request, 'manager/user_edit.html', context)

# -------------------------- 3. 删除用户 --------------------------
def user_delete(request, pk):
    """删除用户（物理删除，确保同时删除关联的登录账号）"""
    # 获取要删除的用户扩展信息
    user_info = get_object_or_404(UserInfo, pk=pk)
    
    # 关键步骤：先删除关联的登录账号（auth_user）
    if user_info.auth_user:  # 先判断是否有关联的登录账号
        user_info.auth_user.delete()  # 主动删除Django内置User记录
    
    # 再删除自定义的UserInfo记录
    user_info.delete()
    
    return redirect('user_manage')

# -------------------------- 4. 快速切换用户状态（禁用/启用） --------------------------
def user_toggle_status(request, pk):
    """快速切换用户的借用资格（无需进入编辑页）"""
    user = get_object_or_404(UserInfo, pk=pk)
    user.is_active = not user.is_active  # 取反：正常→禁用，禁用→正常
    user.save()
    return redirect('user_manage')