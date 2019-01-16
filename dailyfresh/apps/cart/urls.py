from django.urls import path
from . import views
app_name='cart'
urlpatterns = [
    path("add/",views.CartAddView.as_view(),name='add'),#添加购物车
    path("show/",views.CartInfoView.as_view(),name='show'),#显示购物车
    path("update/",views.CartUpdateView.as_view(),name='update'),#购物车记录更新
    path("delete/",views.CartDeleteView.as_view(),name='delete'),#购物车记录删除
]