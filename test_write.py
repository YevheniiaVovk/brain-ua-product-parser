
from modules.load_django import *
from parser_app.models import Product

# Створи тестовий товар
product = Product.objects.create(
    title="Test iPhone 15",
    color="Black",
    memory="128GB",
    manufacturer="Apple",
    price="899$",
    product_code="TEST123",
    reviews_count=42
)

print("✅ Товар записаний в БД:")
print(f"ID: {product.id}")
print(f"Назва: {product.title}")
print(f"Ціна: {product.price}")