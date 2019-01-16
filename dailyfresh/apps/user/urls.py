from django.urls import path,re_path
from django.contrib.auth.decorators import login_required
from . import views
app_name='user'
urlpatterns = [
    path("register/",views.registerView.as_view(),name='register'),#注册
    path("register_exist/",views.register_exist),#注册判断
    path("login/",views.LoginView.as_view(),name='login'),#登陆
    path("info/",views.UserInfoView.as_view(),name='info'),#用户信息
    path('order/<page>/',views.UserOrderView.as_view(),name='order'),#用户订单
    path("address/",views.UserAddressView.as_view(),name='address'),#用户地址
    path("logout/",views.LogoutView.as_view(),name='logout'),#退出
    re_path(r"active/(?P<token>.*)",views.ActiveView.as_view(),name="active"),#激活

]