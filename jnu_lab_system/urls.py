from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # 挂载应用路由
    path('', include('lab_management.urls')),
]