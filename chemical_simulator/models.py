# chemical_simulator/models.py

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
import json

User = get_user_model()


class Species(models.Model):
    """
    Modelo para representar espécies químicas (reagentes/produtos)
    """
    name = models.CharField(max_length=100, unique=True, verbose_name='Nome')
    formula = models.CharField(max_length=50, verbose_name='Fórmula Química')
    molecular_weight = models.FloatField(
        validators=[MinValueValidator(0.1)], 
        verbose_name='Peso Molecular (g/mol)'
    )
    description = models.TextField(blank=True, verbose_name='Descrição')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Espécie Química'
        verbose_name_plural = 'Espécies Químicas'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.formula})"


class ReactionTemplate(models.Model):
    """
    Modelo para templates de reações químicas
    """
    class OrderChoices(models.IntegerChoices):
        ZERO = 0, 'Ordem 0'
        FIRST = 1, 'Ordem 1' 
        SECOND = 2, 'Ordem 2'

    name = models.CharField(max_length=150, verbose_name='Nome da Reação')
    description = models.TextField(verbose_name='Descrição')
    
    # Cinética da reação
    reaction_order = models.IntegerField(
        choices=OrderChoices.choices,
        default=OrderChoices.FIRST,
        verbose_name='Ordem da Reação'
    )
    
    # Espécies envolvidas
    reactants = models.ManyToManyField(
        Species, 
        related_name='reactions_as_reactant',
        verbose_name='Reagentes'
    )
    products = models.ManyToManyField(
        Species,
        related_name='reactions_as_product', 
        verbose_name='Produtos'
    )
    
    # Constante cinética padrão
    rate_constant = models.FloatField(
        validators=[MinValueValidator(0.0001)],
        verbose_name='Constante Cinética (k)'
    )
    
    # Metadados
    created_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        verbose_name='Criado por'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, verbose_name='Ativo')

    class Meta:
        verbose_name = 'Template de Reação'
        verbose_name_plural = 'Templates de Reação'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} (Ordem {self.reaction_order})"


class SimulationRun(models.Model):
    """
    Modelo para execuções/runs de simulação
    """
    class StatusChoices(models.TextChoices):
        PENDING = 'pending', 'Pendente'
        RUNNING = 'running', 'Em Execução'
        COMPLETED = 'completed', 'Concluída'
        FAILED = 'failed', 'Falhada'

    # Identificação
    name = models.CharField(max_length=200, verbose_name='Nome da Simulação')
    template = models.ForeignKey(
        ReactionTemplate,
        on_delete=models.CASCADE,
        verbose_name='Template de Reação'
    )
    
    # Parâmetros da simulação
    initial_concentrations = models.JSONField(
        verbose_name='Concentrações Iniciais',
        help_text='JSON com concentrações iniciais das espécies'
    )
    time_span = models.FloatField(
        validators=[MinValueValidator(0.1)],
        verbose_name='Tempo de Simulação (s)'
    )
    time_points = models.IntegerField(
        validators=[MinValueValidator(10), MaxValueValidator(10000)],
        default=100,
        verbose_name='Pontos Temporais'
    )
    
    # Resultados (serão preenchidos após simulação)
    results = models.JSONField(
        null=True, 
        blank=True,
        verbose_name='Resultados da Simulação'
    )
    
    # Estado da simulação
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
        verbose_name='Estado'
    )
    error_message = models.TextField(
        blank=True,
        verbose_name='Mensagem de Erro'
    )
    
    # Metadados
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Criado por'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name='Concluído em'
    )

    class Meta:
        verbose_name = 'Simulação'
        verbose_name_plural = 'Simulações'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.get_status_display()}"

    def get_initial_concentrations_display(self):
        """Método para exibir concentrações de forma legível"""
        if self.initial_concentrations:
            try:
                conc = json.loads(self.initial_concentrations) if isinstance(self.initial_concentrations, str) else self.initial_concentrations
                return ', '.join([f"{k}: {v}M" for k, v in conc.items()])
            except:
                return "Formato inválido"
        return "Não definidas"
