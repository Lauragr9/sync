# Root URL configuration for the project. Wires up the Django admin, the built-in
# auth URLs (logout, password reset, etc.), the custom login view, and delegates
# all app-level routes to sync/urls.py.
from django.contrib import admin
from django.urls import path, include
from sync.views import CustomLoginView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', CustomLoginView.as_view(), name='login'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('sync.urls')),
]