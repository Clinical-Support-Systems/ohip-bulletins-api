from rest_framework.permissions import BasePermission
from django.conf import settings

class HasStaticAPIKey(BasePermission):   
    # Get the API key from the request header
    def has_permission(self, request, view):
        # Get the API key from the request header
        api_key = request.headers.get('Authorization')
        
        # Check if the API key matches the one defined in environment variables
        expected_api_key = f"Api-Key {settings.API_KEY}"
        
        return api_key == expected_api_key