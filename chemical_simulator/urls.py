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
    
    # Placeholder URLs para Species (vamos criar depois)
    path('species/', views.species_list, name='species_list'),
    
    # Placeholder URLs para Simulations (vamos criar depois)
    path('simulations/', views.simulation_list, name='simulation_list'),
]