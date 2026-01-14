# user/urls.py 完整代码
from django.urls import path
from . import views
from booking.views import booking_apply, cancel_booking, my_booking, device_booking_detail, check_availability

urlpatterns = [
    path('home/', views.user_home, name='user_home'),
    path('device/list/', views.device_list, name='device_list'),
    path('device/booking/<int:device_id>/', device_booking_detail, name='device_booking_detail'),
    path('booking/apply/', booking_apply, name='booking_apply'),
    path('check-availability/', check_availability, name='check_availability'),
    path('booking/my/', my_booking, name='my_booking'),
    path('booking/cancel/<int:booking_id>/', cancel_booking, name='cancel_booking'),
    path('profile/', views.user_profile, name='user_profile'),
    path('change-password/', views.change_password, name='change_password'),
    path('register/', views.register_view, name='register'),

    # 教师专属功能
    path('teacher/approve/', views.teacher_approve, name='teacher_approve'),
    path('student/add/', views.add_student, name='add_student'),
    path('student/add/full/', views.add_student_full, name='add_student_full'),
    path('student/edit/<int:student_id>/', views.edit_student, name='edit_student'),
    path('student/remove/<int:student_id>/', views.remove_student, name='remove_student'),
]