from django.urls import path, include
from . import views
from booking.views import booking_apply, cancel_booking, my_booking

urlpatterns = [
    # 普通用户首页
    path('home/', views.user_home, name='user_home'),
    # 设备查询页
    path('device/list/', views.device_list, name='device_list'),
    # 预约申请页
    path('booking/apply/', booking_apply, name='booking_apply'),
    # 我的预约页
    path('booking/my/', my_booking, name='my_booking'),
    # 删除预约
    path('booking/cancel/<int:booking_id>/', cancel_booking, name='cancel_booking'),
    # 个人信息页
    path('profile/', views.user_profile, name='user_profile'),
    path('change-password/', views.change_password, name='change_password'),
]