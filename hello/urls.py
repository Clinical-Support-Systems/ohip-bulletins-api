from django.urls import path
from .views import OhipBulletinAPIView

urlpatterns = [
    path('search/<str:search>/', OhipBulletinAPIView.as_view(), name='ohipBulletins-api'),
]