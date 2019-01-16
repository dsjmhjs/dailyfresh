from django.shortcuts import render
from django.views import View
from django.http import JsonResponse
from goods.models import GoodsSKU
from django_redis import get_redis_connection
from utils.Mixin import LoginRequireMixin
# Create your views here.

#添加购物车
class CartAddView(View):
    def post(self,request):
        user=request.user
        #判断用户是否登录
        if not user.is_authenticated:
            return JsonResponse({'res':0,'errmsg':"去先登录"})

        #接收数据
        post= request.POST
        sku_id=post.get('sku_id')
        count=post.get('count')

        #数据完整性校验
        if not all([sku_id,count]):
            return JsonResponse({'res':1,'errmsg':"数据不完整"})

         #商品数量是否合法
        try:
            count=int(count)
        except:
            return JsonResponse({'res':2,'errmsg':"商品数目错误"})

        # 商品是否存在
        try:
            sku=GoodsSKU.objects.get(id=sku_id)
        except:
            return JsonResponse({'res': 3, 'errmsg': "商品不存在"})

        #添加数据保存到redis
        conn=get_redis_connection('default')
        cart_key='cart_{}'.format(user.id)

        cart_count=conn.hget(cart_key,sku_id)
        if cart_count:
            count+=int(cart_count)

        #是否超出库存
        if count>sku.stock:
            return JsonResponse({'res': 4, 'errmsg': "商品库存不足"})

        # hget sku_id存在就更新 不存在就添加
        conn.hset(cart_key,sku_id,count)

        #返回购物车条数
        cart_count=conn.hlen(cart_key)

        return JsonResponse({'res':5,'cart_count':cart_count,"message":"添加购物车成功"})

#购物车信息
class CartInfoView(LoginRequireMixin,View):
    def get(self,request):
        #登录用户
        user=request.user
        #获取购物车信息
        conn=get_redis_connection('default')
        cart_key='cart_{}'.format(user.id)
        cart_dict=conn.hgetall(cart_key)
        #遍历获取购物车信息
        skus=[]
        total_count=0
        total_price=0
        for sku_id,count in cart_dict.items():
            #获取商品
            sku=GoodsSKU.objects.get(id=sku_id)
            #商品小计
            amount=sku.price*int(count)
            #动态给sku添加属性
            sku.amount=amount
            sku.count=int(count)
            #购物车商品信息列表
            skus.append(sku)
            #总价格和总数目
            total_count +=int(count)
            total_price += amount
        #组织上下文
        context={
            'total_count':total_count,
            'total_price':total_price,
            'skus':skus
        }
        return render(request,'df_cart\\cart.html',context)

#更新购物车记录
class CartUpdateView(View):
    def post(self,request):
        user = request.user
        # 判断用户是否登录
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': "去先登录"})

        # 接收数据
        post = request.POST
        sku_id = post.get('sku_id')
        count = post.get('count')

        # 数据完整性校验
        if not all([sku_id, count]):
            return JsonResponse({'res': 1, 'errmsg': "数据不完整"})

            # 商品数量是否合法
        try:
            count = int(count)
        except:
            return JsonResponse({'res': 2, 'errmsg': "商品数目错误"})

        # 商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except:
            return JsonResponse({'res': 3, 'errmsg': "商品不存在"})

        # 添加数据保存到redis
        conn = get_redis_connection('default')
        cart_key = 'cart_{}'.format(user.id)
        # 是否超出库存
        if count > sku.stock:
            return JsonResponse({'res': 4, 'errmsg': "商品库存不足"})

        # hget sku_id存在就更新 不存在就添加
        conn.hset(cart_key, sku_id, count)

        # 返回购物车条数
        cart_count = conn.hlen(cart_key)

        #计算购物车商品数量
        total_count=0
        vals=conn.hvals(cart_key)
        for val in vals:
            total_count+=int(val)
        return JsonResponse({'res': 5,'total_count':total_count, 'cart_count': cart_count, "message": "添加购物车成功"})

#购物车删除
class CartDeleteView(View):
    def post(self,request):
        #用户是否登录
        user=request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': "去先登录"})

        #获取要删除商品的id
        sku_id=request.POST.get('sku_id')
        #数据是否完整
        if not sku_id:
            return JsonResponse({'res': 1, 'errmsg': "无效商品id"})

        #商品是否存在
        try:
            sku=GoodsSKU.objects.get(id=sku_id)
        except:
            return JsonResponse({'res': 2, 'errmsg': "商品不存在"})

        #删除购物车记录
        conn=get_redis_connection('default')
        cart_key='cart_{}'.format(user.id)
        conn.hdel(cart_key,sku_id)

        # 计算购物车商品数量
        total_count = 0
        vals = conn.hvals(cart_key)
        for val in vals:
            total_count += int(val)

        return JsonResponse({'res': 3,'total_count':total_count, 'message': "删除成功"})


