from django.shortcuts import render,redirect,reverse
from django.http import HttpResponse,JsonResponse
from django.views import View
from .models import User,Address
from django.conf import settings
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
from django.core.mail import send_mail
from django.contrib.auth import authenticate,login,logout
import django_redis
from utils.Mixin import LoginRequireMixin
from django_redis import get_redis_connection
from goods.models import GoodsSKU
from order.models import OrderInfo,OrderGoods
from django.core.paginator import Paginator
# from celery_tasks.tasks import send_register_active_email
# Create your views here.

#注册
class registerView(View):
    def get(self,request):
        return render(request,'df_user\\register.html')

    def post(self,request):
        # 接收用户输入
        post = request.POST
        uname = post.get('user_name')
        upwd = post.get('pwd')
        ucpwd = post.get('cpwd')
        uemail = post.get('email')
        if not all([uname,upwd,ucpwd,uemail]) and upwd != ucpwd:
            return render(request,'df_user\\register.html')
        else:
            user=User.objects.create_user(uname,uemail,upwd)
            user.is_active=0
            user.save()

            #发邮件
            subject='天天生鲜欢迎信息'
            message=''
            sender=settings.EMAIL_FROM
            receiver=[uemail]
            htmlmessage="<h1>{},欢迎您注册，点击链接激活:</h1><a href='http://127.0.0.1:8000/user/active/{}'>user/active/{}</a>".format(user.username,user.generate_active_token(),user.generate_active_token())
            send_mail(subject, message, sender, receiver, fail_silently=False,html_message=htmlmessage)

            #celery发邮件
            # username=user.username
            # token=user.generate_active_token()
            # send_register_active_emailel.delay(uemail,username,token)
            return redirect(reverve('user:login'))


# 判断用户是否已经存在
def register_exist(requset):
    uname = requset.GET.get('uname')
    count = User.objects.filter(username=uname).count()
    return JsonResponse({'count': count})

#激活
class ActiveView(View):
    def get(self,request,token):
        '''进行用户激活'''
        #进行解密
        serializer=Serializer(settings.SECRET_KEY,3600)
        try:
            info= serializer.loads(token)
            #待激活用户id
            user_id=info['confirm']
            #根据id获取用户信息
            user=User.objects.get(id=user_id)
            user.is_active=1
            user.save()
            return redirect(reverse("user:login"))
        except SignatureExpired as e:
            return HttpResponse("激活链接已过期")

#登录
class LoginView(View):
    def get(self,request):
        #判断是否记住用户名
        if "username" in request.COOKIES:
            username=request.COOKIES.get('username')
            checked='checked'
        else:
            username =''
            checked = ''
        context={
            'username':username,
            'checked':checked
        }
        return render(request,'df_user\login.html',context=context)

    def post(self,request):
        post=request.POST
        username=post.get('username')
        password=post.get('pwd')
        save_user=post.get("save_user")

        #校验用户
        # user=User.objects.filter(username=username,password=password)[0]
        user=authenticate(username=username,password=password)
        if user is not None:
                login(request,user)

                #是否在未登陆之前进入网页
                next_url=request.GET.get('next')
                if next_url is None:
                    response = redirect(reverse("user:info"))
                else:
                    response =redirect(next_url)

                #設置cookies
                save_user=post.get("save_user")
                if save_user=='on':
                    response.set_cookie('username',username,max_age=60*60*24)
                else:
                    response.delete_cookie("username")

                return response
                # return redirect(reverse('goods:index'))


        else:
            #用户名密码错误
            user=User.objects.filter(username=username)
            if user!=1:
                context = {
                    "error_name": 1,
                }
                return render(request, "df_user\login.html", context=context)
            else:
                context={
                    "error_pwd":1
                }
                return render(request,"df_user\login.html",context=context)


#退出登陆
class LogoutView(View):
    def get(self,request):
        logout(request)
        return redirect('/index/')

#用户信息页
class UserInfoView(LoginRequireMixin,View):
    def get(self,request):
        #django会默认给request添加user
        user=request.user
        adders = Address.objects.get_default_address(request.COOKIES.get('username'))
        #获取历史记录
        conne=get_redis_connection('default')
        history_key='history_{}'.format(user.id)
        sku_ids=conne.lrange(history_key,0,4)
        goods_list=[]
        for id in sku_ids:
            goods=GoodsSKU.objects.filter(id=id)[0]
            goods_list.append(goods)

        context = {
            'info': '1',
            'user': user,
            'adders': adders,
            'goods_list': goods_list
        }

        return render(request,'df_user\\user_center_info.html',context=context)


# 用户订单页
class UserOrderView(LoginRequireMixin,View):
    def get(self,request,page):
        #获取登录用户
        user=request.user
        orders=OrderInfo.objects.filter(user=user).order_by('create_time')

        #遍历获取商品信息
        for order in orders:
            #商品信息
            order_skus=OrderGoods.objects.filter(order_id=order.order_id)
            for order_sku in order_skus:
                #计算每件商品的小计
                amount=order_sku.count*order_sku.price
                #动态给order_sku添加属性
                order_sku.amount=amount
            # 动态给order_sku添加属性
            order.order_skus=order_skus
            order.status_name=OrderInfo.ORDER_STATUS[order.order_status]

        # 分页
        paginator = Paginator(orders, 3)

        # 获取第page页数据
        try:
            page = int(page)
        except:
            page = 1

        if page > paginator.num_pages:
            page = 1

        # 获取第page页的page实例对象
        order_page = paginator.page(page)

        num_pages = paginator.num_pages
        if num_pages < 5:
            pages = range(1, num_pages + 1)
        elif page <= 3:
            pages = range(1, 6)

        elif num_pages - page <= 2:
            pages = range(num_pages - 4, num_pages + 1)
        else:
            pages = range(page - 2, page + 3)

        #组织上下文
        context={
            'order_page':order_page,
            'pages':pages,
            'order':orders

        }
        #使用模板
        return render(request,'df_user\\user_center_order.html',context=context)

#用户地址页
class UserAddressView(LoginRequireMixin,View):

    def get(self,request):
        #获取默认地址
        adders =Address.objects.get_default_address(request.COOKIES.get('username'))
        if adders is None:
            adders=Address.objects.filter(user__username=request.COOKIES.get('username')).last()
        #把默认地址返回给模板
        context = {
            'site': '1',
            'addre':adders
        }
        return render(request,'df_user\\user_center_site.html',context=context)

    def post(self,request):
        #获取地址数据
        post=request.POST
        receiver=post.get('name')
        addr=post.get('addr')
        zip_code=post.get('zip_code')
        phone=post.get('phone')
        defaule=post.get('default')
        #是否为默认
        if defaule=='on':
            defaule=True
            #把已经存在的默认地址变为不默认
            adders =Address.objects.get_default_address(request.COOKIES.get('username'))
            if adders is not None:
                adders.is_default=False
                adders.save()

        else:
            defaule = False

        #数据是否完整
        if not all([receiver,addr,phone]):
            return render(request,'df_user\\user_center_site.html')
        try:
            #保存到地址表中
            user=User.objects.get(username=request.COOKIES.get('username'))
            address=Address.objects.create(user=user,receiver=receiver,addr=addr,zip_code=zip_code,phone=phone,is_default=defaule)
            return redirect(reverse("user:address"))
        except Exception as e:
            return redirect(reverse("user:address"))

