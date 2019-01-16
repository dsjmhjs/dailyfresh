from django.urls import path
from . import views
app_name='order'
urlpatterns = [
    path('place/',views.OrderPlaceView.as_view(),name='place'),#订单首页
    path('commit/',views.OrderCommitView.as_view(),name='commit'),#订单创建
    path('pay/',views.OrderPayView.as_view(),name='pay'),#订单支付
    path('check/',views.CheckPayView.as_view(),name='check')#订单支付结果
]