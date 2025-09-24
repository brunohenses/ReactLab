import numpy as np
from scipy.integrate import odeint
import json
from django.utils import timezone
from .models import ReactionTemplate, SimulationRun, Species


class SimulationEngine:
    """Motor de simulação para reações químicas"""
    
    def __init__(self, template, initial_concentrations, time_span, time_points=100):
        self.template = template
        self.initial_concentrations = initial_concentrations
        self.time_span = time_span
        self.time_points = time_points
        self.time_array = np.linspace(0, time_span, time_points)
        
        # Validar dados de entrada
        self._validate_inputs()
        
        # Preparar espécies
        self.reactants = list(template.reactants.all())
        self.products = list(template.products.all())
        self.all_species = self.reactants + self.products
        
        # Criar mapeamento espécie → índice
        self.species_index = {species.pk: i for i, species in enumerate(self.all_species)}
        
    def _validate_inputs(self):
        """Validar parâmetros de entrada"""
        if self.time_span <= 0:
            raise ValueError("Tempo de simulação deve ser positivo")
        
        if self.time_points < 10:
            raise ValueError("Número mínimo de pontos temporais é 10")
        
        if not self.initial_concentrations:
            raise ValueError("Concentrações iniciais são obrigatórias")
        
        # Verificar concentrações positivas
        for species_id, conc in self.initial_concentrations.items():
            if conc < 0:
                raise ValueError(f"Concentração inicial deve ser positiva para espécie {species_id}")
    
    def run_simulation(self):
        """Executar simulação baseada na ordem de reação"""
        try:
            if self.template.reaction_order == 1:
                return self._simulate_first_order()
            elif self.template.reaction_order == 2:
                return self._simulate_second_order()
            elif self.template.reaction_order == 3:
                return self._simulate_third_order()
            else:
                raise ValueError(f"Ordem de reação {self.template.reaction_order} não suportada")
                
        except Exception as e:
            raise SimulationError(f"Erro na simulação: {str(e)}")
    
    def _simulate_first_order(self):
        """Simulação 1ª ordem: -d[A]/dt = k[A]"""
        
        def first_order_ode(concentrations, t):
            """Sistema de EDOs para 1ª ordem"""
            dcdt = np.zeros(len(concentrations))
            k = self.template.rate_constant
            
            # Para cada reagente: -k * [A]
            for i, species in enumerate(self.reactants):
                dcdt[self.species_index[species.pk]] -= k * concentrations[self.species_index[species.pk]]
            
            # Para cada produto: +k * [A_reagente]
            # Assumindo estequiometria 1:1 por simplicidade
            if self.reactants and self.products:
                reactant_consumption = k * concentrations[self.species_index[self.reactants[0].pk]]
                for species in self.products:
                    dcdt[self.species_index[species.pk]] += reactant_consumption / len(self.products)
            
            return dcdt
        
        # Concentrações iniciais ordenadas
        c0 = self._get_initial_concentration_array()
        
        # Resolver EDO
        solution = odeint(first_order_ode, c0, self.time_array)
        
        return self._format_results(solution)
    
    def _simulate_second_order(self):
        """Simulação 2ª ordem: -d[A]/dt = k[A]²"""
        
        def second_order_ode(concentrations, t):
            """Sistema de EDOs para 2ª ordem"""
            dcdt = np.zeros(len(concentrations))
            k = self.template.rate_constant
            
            # Para cada reagente: -k * [A]²
            for i, species in enumerate(self.reactants):
                conc = concentrations[self.species_index[species.pk]]
                dcdt[self.species_index[species.pk]] -= k * conc * conc
            
            # Para cada produto: +k * [A_reagente]²
            if self.reactants and self.products:
                reactant_conc = concentrations[self.species_index[self.reactants[0].pk]]
                product_formation = k * reactant_conc * reactant_conc
                for species in self.products:
                    dcdt[self.species_index[species.pk]] += product_formation / len(self.products)
            
            return dcdt
        
        c0 = self._get_initial_concentration_array()
        solution = odeint(second_order_ode, c0, self.time_array)
        
        return self._format_results(solution)
    
    def _simulate_third_order(self):
        """Simulação 3ª ordem: -d[A]/dt = k[A]³"""
        
        def third_order_ode(concentrations, t):
            """Sistema de EDOs para 3ª ordem"""
            dcdt = np.zeros(len(concentrations))
            k = self.template.rate_constant
            
            # Para cada reagente: -k * [A]³
            for i, species in enumerate(self.reactants):
                conc = concentrations[self.species_index[species.pk]]
                dcdt[self.species_index[species.pk]] -= k * conc * conc * conc
            
            # Para cada produto: +k * [A_reagente]³
            if self.reactants and self.products:
                reactant_conc = concentrations[self.species_index[self.reactants[0].pk]]
                product_formation = k * reactant_conc * reactant_conc * reactant_conc
                for species in self.products:
                    dcdt[self.species_index[species.pk]] += product_formation / len(self.products)
            
            return dcdt
        
        c0 = self._get_initial_concentration_array()
        solution = odeint(third_order_ode, c0, self.time_array)
        
        return self._format_results(solution)
    
    def _get_initial_concentration_array(self):
        """Converter concentrações iniciais para array numpy"""
        c0 = np.zeros(len(self.all_species))
        
        for species in self.all_species:
            species_id_str = str(species.pk)
            if species_id_str in self.initial_concentrations:
                c0[self.species_index[species.pk]] = self.initial_concentrations[species_id_str]
            else:
                # Usar concentração padrão se não fornecida
                c0[self.species_index[species.pk]] = species.default_concentration
        
        return c0
    
    def _format_results(self, solution):
        """Formatar resultados para armazenamento JSON"""
        results = {
            'time': self.time_array.tolist(),
            'species_data': {},
            'metadata': {
                'reaction_order': self.template.reaction_order,
                'rate_constant': self.template.rate_constant,
                'time_span': self.time_span,
                'time_points': self.time_points,
                'timestamp': timezone.now().isoformat()
            }
        }
        
        # Dados de cada espécie
        for species in self.all_species:
            species_index = self.species_index[species.pk]
            results['species_data'][str(species.pk)] = {
                'name': species.name,
                'formula': species.formula,
                'role': 'reactant' if species in self.reactants else 'product',
                'concentrations': solution[:, species_index].tolist(),
                'initial_concentration': solution[0, species_index],
                'final_concentration': solution[-1, species_index]
            }
        
        return results
    
    def get_analytical_solution(self):
        """Calcular solução analítica quando possível (apenas 1 reagente)"""
        if len(self.reactants) != 1:
            return None
        
        reactant = self.reactants[0]
        c0 = float(self.initial_concentrations.get(str(reactant.pk), reactant.default_concentration))
        k = self.template.rate_constant
        
        if self.template.reaction_order == 1:
            # [A](t) = [A]₀ * exp(-kt)
            analytical = c0 * np.exp(-k * self.time_array)
        elif self.template.reaction_order == 2:
            # 1/[A](t) = 1/[A]₀ + kt
            analytical = 1 / (1/c0 + k * self.time_array)
        elif self.template.reaction_order == 3:
            # 1/[A]²(t) = 1/[A]²₀ + 2kt
            analytical = 1 / np.sqrt(1/(c0*c0) + 2*k * self.time_array)
        else:
            return None
        
        return {
            'time': self.time_array.tolist(),
            'concentration': analytical.tolist(),
            'species_name': reactant.name,
            'species_formula': reactant.formula
        }


class SimulationError(Exception):
    """Exceção customizada para erros de simulação"""
    pass


def create_and_run_simulation(template, initial_concentrations, time_span, time_points, user):
    """Função utilitária para criar e executar simulação"""
    
    # Criar registro de simulação
    simulation_run = SimulationRun.objects.create(
        name=f"Simulação {template.name} - {timezone.now().strftime('%d/%m/%Y %H:%M')}",
        template=template,
        initial_concentrations=initial_concentrations,
        time_span=time_span,
        time_points=time_points,
        created_by=user,
        status='running'
    )
    
    try:
        # Executar simulação
        engine = SimulationEngine(template, initial_concentrations, time_span, time_points)
        results = engine.run_simulation()
        
        # Adicionar solução analítica se possível
        analytical = engine.get_analytical_solution()
        if analytical:
            results['analytical_solution'] = analytical
        
        # Salvar resultados
        simulation_run.results = results
        simulation_run.status = 'completed'
        simulation_run.completed_at = timezone.now()
        simulation_run.save()
        
        return simulation_run, None
        
    except Exception as e:
        # Marcar como falhada
        simulation_run.status = 'failed'
        simulation_run.error_message = str(e)
        simulation_run.save()
        
        return simulation_run, str(e)