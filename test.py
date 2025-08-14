# test_views2.py
import os
import django
from django.test import RequestFactory

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "llm_project_app.settings")
django.setup()

# Import your view AFTER setup


# Create a mock request
factory = RequestFactory()
request = factory.get('/triage2')  # Use post() for POST requests

# Call the view function
response = triage2(request)

# Print results
print("Status Code:", response.status_code)
print("Response Content:", response.content.decode())