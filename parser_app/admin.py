from django.contrib import admin
from parser_app.models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'product_code', 'title', 'price', 'sale_price', 'manufacturer', 'parser_source')
    list_filter = ('parser_source', 'manufacturer')
    search_fields = ('title', 'product_code')