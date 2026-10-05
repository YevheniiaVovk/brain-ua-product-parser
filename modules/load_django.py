
import os
import sys
import django

# Path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parser_project.settings')
django.setup()

# Import models
from parser_app.models import Product