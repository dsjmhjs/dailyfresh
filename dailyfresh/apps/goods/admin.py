from django.contrib import admin
from .models import GoodsType,IndexTypeGoodsBanner,IndexPromotionBanner,IndexGoodsBanner,Goods,GoodsSKU,GoodsImage
from django.core.cache import cache
# Register your models here.
class BaseManageAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        cache.delete("index_page_data")
    def delete_model(self, request, obj):
        super().delete_model(request, obj, form, change)

class GoodsTypeAdmin(BaseManageAdmin):
    pass

class IndexTypeGoodsBannerAdmin(BaseManageAdmin):
    pass

class IndexPromotionBannerAdmin(BaseManageAdmin):
    pass

class IndexGoodsBannerAdmin(BaseManageAdmin):
    pass

class GoodsAdmin(BaseManageAdmin):
    pass

class GoodsSKUAdmin(BaseManageAdmin):
    pass

class GoodsImageAdmin(BaseManageAdmin):
    pass

admin.site.register(GoodsType,GoodsTypeAdmin)
admin.site.register(IndexGoodsBanner,IndexTypeGoodsBannerAdmin)
admin.site.register(IndexPromotionBanner,IndexPromotionBannerAdmin)
admin.site.register(IndexTypeGoodsBanner,IndexTypeGoodsBannerAdmin)
admin.site.register(Goods,GoodsAdmin)
admin.site.register(GoodsImage,GoodsImageAdmin)
admin.site.register(GoodsSKU,GoodsSKUAdmin)

