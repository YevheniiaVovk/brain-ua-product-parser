from django.db import models

class Product(models.Model):
    # --- Основне ---
    title = models.CharField(max_length=500, null=True, blank=True)
    color = models.CharField(max_length=100, null=True, blank=True)
    memory = models.CharField(max_length=100, null=True, blank=True)
    manufacturer = models.CharField(max_length=100, null=True, blank=True)
    product_code = models.CharField(max_length=100, null=True, blank=True)
    
    # --- Ціни ---
    price = models.IntegerField(null=True, blank=True)  # Змініть на IntegerField
    sale_price = models.IntegerField(null=True, blank=True)
    
    # --- Фото і характеристики ---
    photos = models.TextField(null=True, blank=True)  # JSON список
    screen_diagonal = models.CharField(max_length=100, null=True, blank=True)
    screen_resolution = models.CharField(max_length=100, null=True, blank=True)
    specifications = models.TextField(null=True, blank=True)  # JSON словник
    reviews_count = models.IntegerField(default=0)
    
    # --- Джерело даних ---
    PARSER_CHOICES = (
        ('requests_bs4', 'Requests / BS4'),
        ('selenium', 'Selenium'),
        ('playwright', 'Playwright'),
    )
    parser_source = models.CharField(
        max_length=20, 
        choices=PARSER_CHOICES, 
        default='requests_bs4'
    )
    
    # --- Служба ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('product_code', 'parser_source')
    
    def __str__(self):
        return self.title or f"Product ({self.product_code})"