from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('signup/', views.signup, name='signup'),
    path('trips/new/', views.trip_create, name='trip_create'),
    path('trips/<slug:slug>/', views.trip_detail, name='trip_detail'),
    path('trips/join/<uuid:token>/', views.trip_join, name='trip_join'),
    path('trips/<slug:slug>/propose/', views.proposal_create, name='proposal_create'),
    path('proposals/<int:proposal_id>/vote/', views.vote, name='vote'),
    path('trips/<slug:slug>/edit/', views.trip_edit, name='trip_edit'),
    path('proposals/<int:proposal_id>/edit/', views.proposal_edit, name='proposal_edit'),
]