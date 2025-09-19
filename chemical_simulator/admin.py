# chemical_simulator/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import Species, ReactionTemplate, SimulationRun


@admin.register(Species)
class SpeciesAdmin(admin.ModelAdmin):
    list_display = ('name', 'formula', 'molecular_weight', 'simulation_role', 'physical_state', 'color', 'created_at')
    list_filter = ('simulation_role', 'physical_state', 'color', 'transparency', 'created_at')
    search_fields = ('name', 'formula', 'cas_number')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('name', 'formula', 'molecular_weight'),
            'description': 'Dados fundamentais da espécie química'
        }),
        ('Propriedades Físicas', {
            'fields': ('density', 'physical_state'),
            'description': 'Características físicas a 25°C'
        }),
        ('Propriedades para Simulação', {
            'fields': ('default_concentration', 'simulation_role'),
            'description': 'Configurações para uso em simulações'
        }),
        ('Propriedades Visuais', {
            'fields': ('color', 'transparency'),
            'description': 'Aparência visual da substância'
        }),
        ('Informações Adicionais', {
            'fields': ('description',),
        }),
        ('Metadados', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Identificação', {
            'fields': ('cas_number',),
            'description': 'Número de registro CAS para identificação única'
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related()


@admin.register(ReactionTemplate)
class ReactionTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'reaction_order', 'rate_constant', 'created_by', 'is_active', 'created_at')
    list_filter = ('reaction_order', 'is_active', 'created_by', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Parâmetros Cinéticos', {
            'fields': ('reaction_order', 'rate_constant'),
            'description': 'Ordem da reação: 1ª, 2ª ou 3ª ordem'
        }),
        ('Espécies Químicas', {
            'fields': ('reactants', 'products'),
            'description': 'Selecione as espécies reagentes e produtos'
        }),
        ('Metadados', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    filter_horizontal = ('reactants', 'products')
    
    def save_model(self, request, obj, form, change):
        """Auto-atribuir o utilizador que criou o template"""
        if not change:  # Apenas para novos objetos
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(SimulationRun)
class SimulationRunAdmin(admin.ModelAdmin):
    list_display = ('name', 'template', 'status', 'created_by', 'created_at', 'completed_at')
    list_filter = ('status', 'created_by', 'created_at')
    search_fields = ('name', 'template__name')
    readonly_fields = ('created_at', 'updated_at', 'completed_at', 'get_initial_concentrations_display')
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('name', 'template', 'status')
        }),
        ('Parâmetros de Simulação', {
            'fields': ('initial_concentrations', 'get_initial_concentrations_display', 'time_span', 'time_points')
        }),
        ('Resultados', {
            'fields': ('results', 'error_message'),
            'classes': ('collapse',)
        }),
        ('Metadados', {
            'fields': ('created_by', 'created_at', 'updated_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Auto-atribuir o utilizador que criou a simulação"""
        if not change:  # Apenas para novos objetos
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_initial_concentrations_display(self, obj):
        """Exibir concentrações de forma legível no admin"""
        return obj.get_initial_concentrations_display()
    get_initial_concentrations_display.short_description = 'Concentrações Iniciais (legível)'


# Customizar o título do admin
admin.site.site_header = "Simulador de Reações Químicas - Administração"
admin.site.site_title = "Simulador Químico"
admin.site.index_title = "Painel de Administração"