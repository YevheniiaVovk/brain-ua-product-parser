# modules/load_django.py

import os
import sys
import django

# Додай шлях до проєкту
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))

# Налаштування Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parser_project.settings')
django.setup()

# Тепер можеш імпортувати моделі
from parser_app.models import Product