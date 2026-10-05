import csv
from modules.load_django import *
from parser_app.models import Product


def export_products_to_csv(filename='products.csv'):
    products = Product.objects.all().values()
    if not products:
        print('[INFO] No products found in database.')
        return

    fieldnames = list(products[0].keys())

    with open(filename, mode='w', encoding='utf-8', newline='') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for product in products:
            writer.writerow(product)

    print(f'[SUCCESS] Exported {len(products)} products to {filename}')


if __name__ == '__main__':
    export_products_to_csv()