# from celery import Celery
# from django.conf import settings
# from django.core.mail import send_mail
# import time
# #创建一个celery
# Celery("celery_tasks.tasks",broker=settings.REDIS_URL)
#
# #任务函数
# @app.task
# def send_register_active_email(to_email,username,token):
#     # 发邮件
#     subject = '天天生鲜欢迎信息'
#     message = ''
#     sender = settings.EMAIL_FROM
#     receiver = [to_email]
#     htmlmessage = "<h1>{},欢迎您注册，点击链接激活:</h1><a href='http://127.0.0.1:8000/user/active/{}'>user/active/{}</a>".format(
#         username, token,token)
#     send_mail(subject, message, sender, receiver, fail_silently=False, html_message=htmlmessage)
#     time.sleep(5)