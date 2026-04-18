from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('signup/', views.signup, name='signup'),
    path('trips/new/', views.trip_create, name='trip_create'),
    path('trips/<slug:slug>/', views.trip_detail, name='trip_detail'),
    path('trips/join/<uuid:token>/', views.trip_join, name='trip_join'),
]