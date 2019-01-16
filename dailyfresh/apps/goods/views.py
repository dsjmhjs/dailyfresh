from django.shortcuts import render,redirect,reverse
from .models import GoodsType,GoodsSKU,Goods,IndexGoodsBanner,IndexPromotionBanner,IndexTypeGoodsBanner
from order.models import OrderGoods
from django.views import View
from django.core.cache import cache
from django_redis import get_redis_connection
from django.core.paginator import Paginator
# Create your views here.

#首页
class IndexView(View):
    def get(self,request):
        context=cache.get('index_page_data')
        if context is None:
            #商品种类
            types=GoodsType.objects.all()
            #轮播商品
            goods_banners=IndexGoodsBanner.objects.all().order_by('index')
            # 促销活动商品
            promotion_banners=IndexPromotionBanner.objects.all().order_by('index')
            #首页分类商品展示信息
            for type in types:
                #图片展示
                image_banners=IndexTypeGoodsBanner.objects.filter(type=type,display_type=1).order_by("index")
               #标题展示
                title_banners=IndexTypeGoodsBanner.objects.filter(type=type,display_type=0).order_by("index")
                #动态给type添加属性
                type.image_banners=image_banners
                type.title_banners=title_banners
            context={
                'types':types,
                'goods_banners':goods_banners,
                'promotion_banners':promotion_banners,

            }
            # cache.set('index_page_data',context,3600)

        user=request.user
        cart_count=0
        #获取购物车信息
        if user.is_authenticated:
            conn=get_redis_connection('default')
            cart_key='cart_{}'.format(user.id)
            cart_count=conn.hlen(cart_key)

        context.update(cart_count=cart_count)

        return render(request,'df_goods\\index.html',context)

#商品详情页
class DetailView(View):
    def get(self,request,goods_id):
        try:
            sku=GoodsSKU.objects.get(id=goods_id)
        except:
            #商品不存在
            return redirect(reverse("goods:index"))
        #商品分类信息
        types=GoodsType.objects.all()
        #商品评论信息
        sku_order=OrderGoods.objects.filter(sku=sku).exclude(comment='')
        #新品信息 前两个
        new_sku=GoodsSKU.objects.filter(type=sku.type).order_by('create_time')[:2]
       #获取同一个spu下的不同sku商品
        same_spu_skus=GoodsSKU.objects.filter(goods=sku.goods).exclude(id=goods_id)
        #购物车信息和历史记录
        user = request.user
        cart_count=0
        if user.is_authenticated:
            #购物车信息
            conn = get_redis_connection('default')
            cart_key = 'cart_{}'.format(user.id)
            cart_count = conn.hlen(cart_key)

            #历史记录
            conn = get_redis_connection('default')
            history_key='history_{}'.format(user.id)
            #移除已存在的goods_id
            conn.lrem(history_key,0,goods_id)
            #添加历史信息
            conn.lpush(history_key,goods_id)
            #截取保存前五条历史最新商品信息
            conn.ltrim(history_key,0,4)



        #组织模板上下文
        context={
            'sku':sku,
            'types':types,
            'sku_orders':sku_order,
            'new_skus':new_sku,
            'cart_count':cart_count,
            'same_spu_skus':same_spu_skus
        }
        #使用模板
        return render(request,'df_goods\\detail.html',context=context)

#列表页
class ListView(View):
    def get(self,request,type_id,page):
        #获取种类信息
        try:
            type=GoodsType.objects.get(id=type_id)
        except:
            #种类不存在
            return render(reverse('goods:index'))

        #获取商品分类信息
        types=GoodsType.objects.all()

        #获取排序方式
        sort=request.GET.get('sort')
        if sort=='price':
            skus=GoodsSKU.objects.filter(type=type).order_by('price')
        elif sort=='hot':
            skus=GoodsSKU.objects.filter(type=type).order_by("-sales")
        else:
            sort='default'
            skus=GoodsSKU.objects.filter(type=type).order_by("-id")

        #分页
        paginator=Paginator(skus,1)

        #获取第page页数据
        try:
            page=int(page)
        except:
            page=1

        if page>paginator.num_pages:
            page=1

        #获取第page页的page实例对象
        skus_page = paginator.page(page)

        num_pages=paginator.num_pages
        if num_pages<5:
            pages=range(1,num_pages+1)
        elif page<=3:
            pages=range(1,6)

        elif num_pages-page<=2:
            pages=range(num_pages-4,num_pages+1)
        else:
            pages=range(page-2,page+3)


        # 新品信息 前两个
        new_sku = GoodsSKU.objects.filter(type=type).order_by('create_time')[:2]

        # 购物车信息和历史记录
        user = request.user
        cart_count = 0
        if user.is_authenticated:
            # 购物车信息
            conn = get_redis_connection('default')
            cart_key = 'cart_{}'.format(user.id)
            cart_count = conn.hlen(cart_key)

        #组织模板上下文
        context={
            'type':type,
            'types':types,
            'new_skus':new_sku,
            'cart_count':cart_count,
            'skus_page':skus_page,
            'sort':sort,
            'pages':pages

        }

        return render(request,'df_goods\\list.html',context)

