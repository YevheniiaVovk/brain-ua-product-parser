from modules.load_django import *
from parser_app.models import Product

# Create test product
product = Product.objects.create(
    title="Test iPhone 15",
    color="Black",
    memory="128GB",
    manufacturer="Apple",
    price="899$",
    product_code="TEST123",
    reviews_count=42
)

print("✅ Added:")
print(f"ID: {product.id}")
print(f"Title: {product.title}")
print(f"Price: {product.price}")