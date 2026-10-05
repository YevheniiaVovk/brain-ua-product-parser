

from modules.load_django import *
from parser_app.models import Product

# Прочитай все з БД
products = Product.objects.all()

print("✅ Товари в БД:")
print(f"Всього: {products.count()}")

for product in products:
    print(f"\n{'='*50}")
    print(f"ID: {product.id}")
    print(f"Назва: {product.title}")
    print(f"Колір: {product.color}")
    print(f"Памʼять: {product.memory}")
    print(f"Виробник: {product.manufacturer}")
    print(f"Ціна: {product.price}")
    print(f"Акційна ціна: {product.sale_price}")
    print(f"Код товару: {product.product_code}")
    print(f"Кількість відгуків: {product.reviews_count}")