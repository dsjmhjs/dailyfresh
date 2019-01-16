from django.urls import path,re_path
from . import views
app_name='goods'
urlpatterns = [
    path("index/",views.IndexView.as_view(),name="index"),#首页
    path("detail/<goods_id>/",views.DetailView.as_view(),name="detail"),#是详情页
    path("list/<type_id>/<page>/",views.ListView.as_view(),name="list"),#列表页
]