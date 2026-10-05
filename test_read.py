

from modules.load_django import *
from parser_app.models import Product


products = Product.objects.all()

print("✅ Goods in DB:")
print(f"All: {products.count()}")

for product in products:
    print(f"\n{'='*50}")
    print(f"ID: {product.id}")
    print(f"Title: {product.title}")
    print(f"Colour: {product.color}")
    print(f"Memory: {product.memory}")
    print(f"Manufacturer: {product.manufacturer}")
    print(f"Price: {product.price}")
    print(f"Sale price: {product.sale_price}")
    print(f"Product code: {product.product_code}")
    print(f"Reviews count: {product.reviews_count}")