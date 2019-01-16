from django.shortcuts import render,redirect,reverse
from django.views import View
from goods.models import GoodsSKU
from django_redis import get_redis_connection
from user.models import Address
from utils.Mixin import LoginRequireMixin
from django.http import JsonResponse
from order.models import OrderInfo,OrderGoods
from datetime import datetime
from django.db import transaction
from alipay import AliPay,ISVAliPay
import os,sys
# Create your views here.

#订单
class OrderPlaceView(LoginRequireMixin,View):
    def post(self,request):
        #获取登录用户
        user=request.user
        #获取订单商品id
        sku_ids=request.POST.getlist('sku_id')
        #如果没有订单id 回到购物车
        if not sku_ids:
            return redirect(reverse('cart:show'))

        #连接redis
        conn=get_redis_connection('default')
        cart_key='cart_{}'.format(user.id)
        #遍历所有订单id 获取商品信息
        skus=[]
        # 商品总数量
        total_count=0
        # 商品总价格
        total_price=0
        for sku_id in sku_ids:
            #商品
            sku=GoodsSKU.objects.get(id=sku_id)
            #商品数量
            count=conn.hget(cart_key,sku_id)
            #商品小计
            amount=sku.price*int(count)
            #动态添加属性
            sku.count=int(count)
            sku.amount=amount
            skus.append(sku)
            #商品总数量
            total_count+=int(count)
            # 商品总价格
            total_price+=amount
        #运费
        transit_price=10
        #实付费
        total_pay=transit_price+total_price
        #收货地址
        addrs=Address.objects.filter(user=user)
        #组织上下文
        context={
            'skus':skus,
            'total_count':total_count,
            'total_price':total_price,
            'total_pay':total_pay,
            'addrs':addrs,
            'sku_ids':','.join(sku_ids)
        }
        return render(request,'df_order\\place_order.html',context)

#订单创建
class OrderCommitView(View):
    #添加事务
    @transaction.atomic
    def post(self,request):
        post=request.POST
        user=request.user
        #判断用户是否登陆
        if not user.is_authenticated:
            #用户未登陆
            return JsonResponse({'res':0,'errmsg':'用户未登陆'})
        #接收参数
        addr_id=post.get('addr_id')
        sku_ids=post.get('sku_ids')
        pay_method=post.get('pay_method')

        #校验参数完整性
        if not all([addr_id,sku_ids,pay_method]):
            return JsonResponse({'res':1,'errmsg':'参数不完整'})

        #校验支付方式
        if pay_method not in [str(i[0]) for i in OrderInfo.PAY_METHOD_CHOICES]:
            return JsonResponse({'res':2,'errmsg':'没有此支付方式，请重新选择'})

        #校验地址是否存在
        try:
            addr=Address.objects.get(id=addr_id)
        except:
            return JsonResponse({'res':3,'errmsg':'地址不存在'})

        #在订单表中添加记录
        #组织参数
        order_id=datetime.now().strftime('%Y%m%d%H%M%S')+str(user.id)
        total_count=0
        total_price=0
        transit_price=10
        #设置事务保存点
        save_id=transaction.savepoint()
        try:
            order=OrderInfo.objects.create(
                order_id=order_id,
                user=user,
                addr=addr,
                pay_method=pay_method,
                total_count=total_count,
                total_price=total_price,
                transit_price=transit_price
            )

            #从redis中获取购买商品信息
            conn=get_redis_connection('default')
            cart_key='cart_{}'.format(user.id)
            sku_ids=sku_ids.split(',')
            # 在订单商品表中添加记录
            for sku_id in sku_ids:
                #商品是否存在
                try:
                    #加悲观锁 select * from table where id=num for update;
                    # sku = GoodsSKU.objects.select_for_update().get(id=sku_id)
                    sku=GoodsSKU.objects.get(id=sku_id)
                except:
                    #回滚
                    transaction.rollback()
                    return JsonResponse({'res': 4, 'errmsg': '商品不存在'})

                #获取商品数量
                count=int(conn.hget(cart_key,sku_id))

                # 判断库存
                if int(count) > sku.stock:
                    # 回滚
                    transaction.rollback()
                    return JsonResponse({'res': 5, 'errmsg': '商品库存不足'})
                # 在订单商品表中添加记录
                OrderGoods.objects.create(
                    order=order,
                    sku=sku,
                    count=count,
                    price=sku.price
                )

                #乐观锁 update table set stock=new_stock,sale=new_sale where id=sku_id and stock=old_stock
                # old_stock=sku.stock
                # new_stock=old_stock-int(count)
                # new_sales=sku.sales=int(count)
                # r=GoodsSKU.objects.filter(id=sku_id,stock=old_stock).update(stock=new_stock,sales=new_sales)
                # if r==0:
                #     transaction.rollback(save_id)
                #     return JsonResponse({'res': 5, 'errmsg': '添加订单失败'})
                #加循环进行三次尝试
                #修改mysql事务隔离的级别为可提交读 修改日志文件

                #更新库存和销量
                sku.stock-=int(count)
                sku.sales+=int(count)
                sku.save()
                #更新订单表中的总数量和总价格
                amount=sku.price*int(count)
                total_count+=int(count)
                total_price+=amount
                order.total_count=total_count
                order.total_price=total_price
                order.save()
        except:
            # 回滚save_id保存点
            transaction.rollback(save_id)
            return JsonResponse({'res':6, 'message': '添加订单失败！！1'})

        #删除购物车记录
        conn = get_redis_connection('default')
        conn.hdel(cart_key,*sku_ids)
        return JsonResponse({'res': 7, 'message': '添加订单成功'})


#订单支付
class OrderPayView(View):
    def post(self,request):
        #用户是否登录
        user=request.user
        if not user.is_authenticated:
            return JsonResponse({'res':0,'errmsg':'用户未登录'})

        # 接收参数
        order_id=request.POST.get('order_id')

        #校验参数
        if not order_id:
            return JsonResponse({'res': 1, 'errmsg': '无效订单id'})
        try:
            order=OrderInfo.objects.get(order_id=order_id,user=user,pay_method=3,order_status=1)
        except Exception  as e:
            return JsonResponse({'res': 2, 'errmsg': '订单错误'})

        #使用python sdk调用支付宝支付接口
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        app_private_key_string = open(os.path.join(BASE_DIR,"order/app_private_key.pem")).read()
        alipay_public_key_string = open(os.path.join(BASE_DIR,"order/alipay_public_key.pem")).read()
        alipay = AliPay(
            appid="2016092400588715",#应用appid
            app_notify_url=None,  # 默认回调url
            app_private_key_string=app_private_key_string,
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_string=alipay_public_key_string,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug = True  # 默认False
        )
        #调用支付接口
        #电脑网站支付# 电脑网站支付，需要跳转到https://openapi.alipaydev.com/gateway.do? + order_string
        total_pay=order.total_price+order.transit_price
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,
            total_amount=str(total_pay),
            subject='天天生鲜_{}'.format(user.id),
            return_url=None,
            notify_url=None  # 可选, 不填则使用默认notify url
        )
        #跳转的沙箱alipaydev地址
        pay_url='https://openapi.alipaydev.com/gateway.do?' + order_string
        #返回应答
        return JsonResponse({'res':3,'pay_url':pay_url})



#支付结果
class CheckPayView(View):
    def post(self,request):
        # 用户是否登录
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

        # 接收参数
        order_id = request.POST.get('order_id')

        # 校验参数
        if not order_id:
            return JsonResponse({'res': 1, 'errmsg': '无效订单id'})
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user, pay_method=3, order_status=1)
        except Exception  as e:
            return JsonResponse({'res': 2, 'errmsg': '订单错误'})

        # 使用python sdk调用支付宝支付接口
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        app_private_key_string = open(os.path.join(BASE_DIR, "order/app_private_key.pem")).read()
        alipay_public_key_string = open(os.path.join(BASE_DIR, "order/alipay_public_key.pem")).read()
        alipay = AliPay(
            appid="2016092400588715",  # 应用appid
            app_notify_url=None,  # 默认回调url
            app_private_key_string=app_private_key_string,
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_string=alipay_public_key_string,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=True  # 默认False
        )
        while True:
            # 调用支付宝查询交易接口的返回结果
            response=alipay.api_alipay_trade_query(order_id)
            # 验证alipay的异步通知，data来自支付宝回调POST 给你的data，字典格式.

            #调用支付宝查询交易接口
            code = response.get('code')
            if code=='10000' and response.get('trade_status')=='TRADE_SUCCESS':
                #支付成功
                #获取支付交易码
                trade_no=response.get('trade_no')
                #更新订单状态
                order.trade_no=trade_no
                order.order_status=4 #待评价
                order.save()
                return JsonResponse({'res': 3, 'message': '支付成功'})
            elif code=='40004' or (code=='10000' and response.get('trade_status')=='WAIT_BUYER_PAY'):
                import time
                time.sleep(5)
                continue
            else:
                #支付失败
                return JsonResponse({'res': 4, 'errmsg': '支付失败'})







