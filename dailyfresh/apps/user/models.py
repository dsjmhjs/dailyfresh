from django.db import models
from django.contrib.auth.models import  AbstractUser
from db.base_model import BaseModel
from django.conf import settings
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
# Create your models here.

class User(AbstractUser,BaseModel):
    '''用户模型'''
    def generate_active_token(self):
        serializer=Serializer(settings.SECRET_KEY,3600)
        info={'confirm':self.id}
        token=serializer.dumps(info)
        return token.decode()

    class Meta:
        db_table='df_user'
        verbose_name='用户'
        verbose_name_plural=verbose_name

#地址模型管理类
class AddressManager(models.Manager):
    #获取默认设置
    def get_default_address(self,user):
        address=self.model
        try:
            addre =self.get(user__username=user,is_default=True)
            return addre
        except:
            return None

class Address(BaseModel):
    '''地址模型'''
    user=models.ForeignKey('User',verbose_name='所属账户',on_delete=models.CASCADE)
    receiver=models.CharField(max_length=20,verbose_name='收件人')
    addr=models.CharField(max_length=256,verbose_name='收件地址')
    zip_code=models.CharField(max_length=6,null=True,verbose_name='邮政编码')
    phone=models.CharField(max_length=11,verbose_name='联系电话')
    is_default=models.BooleanField(default=False,verbose_name='是否默认')
    objects=AddressManager()
    class Meta:
        db_table='df_address'
        verbose_name='地址'
        verbose_name_plural=verbose_name




