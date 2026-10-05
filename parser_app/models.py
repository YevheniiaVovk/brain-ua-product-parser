from django.db import models


class Product(models.Model):
    # --- Main info ---
    title = models.CharField(max_length=500, null=True, blank=True)
    color = models.CharField(max_length=100, null=True, blank=True)
    memory = models.CharField(max_length=100, null=True, blank=True)
    manufacturer = models.CharField(max_length=100, null=True, blank=True)
    product_code = models.CharField(max_length=100)

    # --- Prices ---
    price = models.IntegerField(null=True, blank=True)
    sale_price = models.IntegerField(null=True, blank=True)

    # --- Photos and specifications ---
    photos = models.JSONField(null=True, blank=True)  # list of links
    screen_diagonal = models.CharField(max_length=100, null=True, blank=True)
    screen_resolution = models.CharField(max_length=100, null=True, blank=True)
    specifications = models.JSONField(null=True, blank=True)  # dict {name: value}
    reviews_count = models.IntegerField(null=True, blank=True)

    # --- Data source ---
    PARSER_CHOICES = (
        ('requests_bs4', 'Requests / BS4'),
        ('selenium', 'Selenium'),
        ('playwright', 'Playwright'),
    )
    parser_source = models.CharField(
        max_length=20,
        choices=PARSER_CHOICES,
        default='requests_bs4',
    )

    # --- Service fields ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title or f'Product ({self.product_code})'

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['product_code', 'parser_source'],
                name='unique_product_per_parser',
            )
        ]