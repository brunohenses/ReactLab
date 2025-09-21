# chemical_simulator/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # ReactionTemplate URLs
    path('templates/', views.reaction_template_list, name='reaction_template_list'),
    path('templates/<int:pk>/', views.reaction_template_detail, name='reaction_template_detail'),
    path('templates/create/', views.reaction_template_create, name='reaction_template_create'),
    path('templates/<int:pk>/edit/', views.reaction_template_update, name='reaction_template_update'),
    path('templates/<int:pk>/delete/', views.reaction_template_delete, name='reaction_template_delete'),
    
    # Species URLs
    path('species/', views.species_list, name='species_list'),
    path('species/<int:pk>/', views.species_detail, name='species_detail'),
    path('species/create/', views.species_create, name='species_create'),
    path('species/<int:pk>/edit/', views.species_update, name='species_update'),
    path('species/<int:pk>/delete/', views.species_delete, name='species_delete'),
    
    # CSV Import
    path('species/import-csv/', views.species_csv_import, name='species_csv_import'),
    path('species/csv-template/', views.species_csv_template, name='species_csv_template'),    
    
    
    # Placeholder URLs para Simulations (vamos criar depois)
    path('simulations/', views.simulation_list, name='simulation_list'),
]