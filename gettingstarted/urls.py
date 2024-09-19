"""
URL configuration for gettingstarted project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

# from django.contrib import admin
from django.urls import path, include
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
import hello.views

schema_view = get_schema_view(
    openapi.Info(
        title="OHIP Bulletins API",
        default_version='v1',
        description="API to retrieve OHIP Bulletins Information",
        contact=openapi.Contact(email="fukchr@gmail.com"),
        ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path("", hello.views.index, name="index"),
    path("db/", hello.views.db, name="db"),
    path("api/", include("hello.urls")),
    
    # OpenAPI documentation routes
    path('swagger.yaml', schema_view.without_ui(cache_timeout=0), name='schema-yaml'),  # OpenAPI schema in YAML
    path('swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),  # OpenAPI schema in JSON
    

    # Uncomment this and the entry in `INSTALLED_APPS` if you wish to use the Django admin feature:
    # https://docs.djangoproject.com/en/5.1/ref/contrib/admin/
    # path("admin/", admin.site.urls),
]
