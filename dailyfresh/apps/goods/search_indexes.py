#定义搜索引擎
from haystack import indexes
#要搜索的模型类
from goods.models import GoodsSKU

#指定对于每个模型的某些数据建立索引
class GoodsSKUIndex(indexes.SearchIndex,indexes.Indexable):
    #索引字段 use_template=True 指定根据表中的哪些字段建立索引文件的说明 放在一个文件中
    text=indexes.CharField(document=True,use_template=True)

    def get_model(self):
        #返回模型类
        return GoodsSKU

    #建立索引的数据
    def index_queryset(self, using=None):
        return self.get_model().objects.all()
