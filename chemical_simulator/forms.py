from django import forms
from django.forms.widgets import SelectMultiple
from .models import ReactionTemplate, Species, SimulationRun

class ReactionTemplateForm(forms.ModelForm):
    class Meta:
        model = ReactionTemplate
        fields = ['name', 'description', 'reaction_order', 'rate_constant', 'reactants', 'intermediates', 'products', 'is_active']
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome da reação (ex: Neutralização HCl + NaOH)'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Descrição detalhada da reação química...'
            }),
            'reaction_order': forms.Select(attrs={
                'class': 'form-select'
            }),
            'rate_constant': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.0001',
                'min': '0.0001',
                'placeholder': '0.01'
            }),
            
            # Usar seleção múltipla de espécies
            'reactants': SelectMultiple(attrs={
                'class': 'form-control',
                'style': 'display: none;',
            }),
            'products': SelectMultiple(attrs={
                'class': 'form-control',
                'style': 'display: none;',
            }),
            'intermediates': SelectMultiple(attrs={
                'class': 'form-control',
                'style': 'display: none;',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-control',
                'style': 'display: none;',
            })
        }
        
        labels = {
            'name': 'Nome da Reação',
            'description': 'Descrição',
            'reaction_order': 'Ordem da Reação',
            'rate_constant': 'Constante Cinética (k)',
            'reactants': 'Reagentes',
            'products': 'Produtos',
            'is_active': 'Ativo'
        }
        
        help_texts = {
            'rate_constant': 'Valor da constante cinética (deve ser > 0.0001)',
            'reactants': 'Selecione as espécies que são reagentes (Ctrl+Click para múltipla seleção)',
            'products': 'Selecione as espécies que são produtos (Ctrl+Click para múltipla seleção)'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Garantir que todos os campos tenham todas as espécies como opção
        all_species = Species.objects.all().order_by('name')
    
        self.fields['reactants'].queryset = all_species
        self.fields['intermediates'].queryset = all_species
        self.fields['products'].queryset = all_species
        
        # Adicionar classes CSS e data attributes
        self.fields['reactants'].widget.attrs.update({
            'data-role': 'reactants',
            'data-default-filter': 'reactant,intermediate'
        })
        
        self.fields['intermediates'].widget.attrs.update({
            'data-role': 'intermediates',
            'data-default-filter': 'intermediate'
        })
        
        self.fields['products'].widget.attrs.update({
            'data-role': 'products',
            'data-default-filter': 'product,intermediate'
        })

        for field_name in ['reactants', 'intermediates', 'products']:
            field = self.fields[field_name]
            original_create_option = field.widget.create_option
            
            def create_option_with_role(name, value, label, selected, index, subindex=None, attrs=None):
                option = original_create_option(name, value, label, selected, index, subindex, attrs)
                
                # ✅ CORREÇÃO: value pode ser um ModelChoiceIteratorValue
                if value and hasattr(value, 'value'):
                    pk = value.value
                else:
                    pk = value
                
                if pk:
                    try:
                        species = Species.objects.get(pk=pk)
                        option['attrs']['data-role'] = species.simulation_role
                    except Species.DoesNotExist:
                        pass
                return option
            
            field.widget.create_option = create_option_with_role

    def clean(self):
        cleaned_data = super().clean()
        reactants = cleaned_data.get('reactants')
        products = cleaned_data.get('products')
        
        # Validar reagentes
        if not reactants:
            self.add_error('reactants', "Selecione pelo menos 1 reagente.")
        
        # Validar produtos
        if not products:
            self.add_error('products', "Selecione pelo menos 1 produto.")
        
        # Validar sobreposição (exceto intermediários)
        if reactants and products:
            overlap = set(reactants) & set(products)
            if overlap:
                non_intermediate_overlap = [
                    s for s in overlap 
                    if s.simulation_role != 'intermediate'
                ]
                if non_intermediate_overlap:
                    species_names = ', '.join([s.name for s in non_intermediate_overlap])
                    self.add_error(None, f"As seguintes espécies não podem ser reagentes e produtos simultaneamente: {species_names}")
        
        return cleaned_data
    def clean_rate_constant(self):
        rate_constant = self.cleaned_data.get('rate_constant')
        if rate_constant is not None and rate_constant <= 0:
            raise forms.ValidationError("A constante cinética deve ser maior que zero.")
        return rate_constant
        

# Nova form para gestão rápida de associações
class TemplateSpeciesAssociationForm(forms.Form):
    """Formulário para gerir associações species-template de forma visual"""
    
    def __init__(self, template=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.template = template
        
        if template:
            # Criar campos dinâmicos para cada espécie
            all_species = Species.objects.all().order_by('simulation_role', 'name')
            
            for species in all_species:
                # Campo para definir se é reagente
                self.fields[f'reactant_{species.pk}'] = forms.BooleanField(
                    required=False,
                    initial=species in template.reactants.all(),
                    label=f'{species.name} como reagente'
                )
                
                # Campo para definir se é produto
                self.fields[f'product_{species.pk}'] = forms.BooleanField(
                    required=False,
                    initial=species in template.products.all(),
                    label=f'{species.name} como produto'
                )
    
    def save(self):
        """Salvar as associações"""
        if not self.template:
            return
        
        # Limpar associações existentes
        self.template.reactants.clear()
        self.template.products.clear()
        
        # Aplicar novas associações
        for field_name, value in self.cleaned_data.items():
            if value and field_name.startswith('reactant_'):
                species_pk = field_name.replace('reactant_', '')
                species = Species.objects.get(pk=species_pk)
                self.template.reactants.add(species)
            
            elif value and field_name.startswith('product_'):
                species_pk = field_name.replace('product_', '')
                species = Species.objects.get(pk=species_pk)
                self.template.products.add(species)
    
class SpeciesForm(forms.ModelForm):
    class Meta:
        model = Species
        fields = [
            'name', 'formula', 'molecular_weight', 'density', 'physical_state',
            'default_concentration', 'simulation_role', 'color', 'transparency',
            'description', 'cas_number'
        ]
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome da espécie (ex: Água, Cloreto de Sódio)'
            }),
            'formula': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'H2O, NaCl, HCl'
            }),
            'molecular_weight': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.001',
                'min': '0.1',
                'placeholder': '18.015'
            }),
            'density': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.001',
                'min': '0.001',
                'placeholder': '1.000'
            }),
            'physical_state': forms.Select(attrs={
                'class': 'form-select'
            }),
            'default_concentration': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.0001',
                'min': '0.0001',
                'max': '100',
                'placeholder': '1.0'
            }),
            'simulation_role': forms.Select(attrs={
                'class': 'form-select'
            }),
            'color': forms.Select(attrs={
                'class': 'form-select'
            }),
            'transparency': forms.Select(attrs={
                'class': 'form-select'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descrição da espécie química...'
            }),
            'cas_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '7732-18-5',
                'pattern': '[0-9]{2,7}-[0-9]{2}-[0-9]'
            })
        }
        
        labels = {
            'name': 'Nome',
            'formula': 'Fórmula Química',
            'molecular_weight': 'Peso Molecular (g/mol)',
            'density': 'Densidade (g/cm³)',
            'physical_state': 'Estado Físico (25°C)',
            'default_concentration': 'Concentração Padrão Sugerida (mol·L⁻¹)',
            'simulation_role': 'Papel na Simulação',
            'color': 'Cor',
            'transparency': 'Transparência',
            'description': 'Descrição',
            'cas_number': 'Número CAS'
        }
        
        help_texts = {
            'molecular_weight': 'Peso molecular em gramas por mol',
            'density': 'Densidade a 25°C (opcional para gases)',
            'default_concentration': 'Concentração típica para simulações',
            'cas_number': 'Número de registro CAS (formato: XXXXX-XX-X)'
        }

    def clean_cas_number(self):
        cas_number = self.cleaned_data.get('cas_number', '').strip()
        if cas_number:
            # Validação básica do formato CAS
            import re
            if not re.match(r'^\d{2,7}-\d{2}-\d$', cas_number):
                raise forms.ValidationError(
                    "Formato de CAS inválido. Use o formato: XXXXX-XX-X (ex: 7732-18-5)"
                )
        return cas_number

    def clean_formula(self):
        formula = self.cleaned_data.get('formula', '').strip()
        if not formula:
            raise forms.ValidationError("Fórmula química é obrigatória.")
        
        # Validação básica da fórmula (apenas caracteres permitidos)
        import re
        if not re.match(r'^[A-Za-z0-9\(\)\[\]\+\-\·\s]+$', formula):
            raise forms.ValidationError(
                "Fórmula contém caracteres inválidos. Use apenas letras, números e símbolos químicos básicos."
            )
        return formula

class SpeciesCSVImportForm(forms.Form):
    csv_file = forms.FileField(
        label='Arquivo CSV',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv'
        }),
        help_text='Selecione um arquivo CSV com as espécies químicas'
    )
    
    def clean_csv_file(self):
        csv_file = self.cleaned_data['csv_file']
        
        # Verificar extensão
        if not csv_file.name.lower().endswith('.csv'):
            raise forms.ValidationError("Arquivo deve ter extensão .csv")
        
        # Verificar tamanho (máximo 5MB)
        if csv_file.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Arquivo muito grande. Máximo permitido: 5MB")
        
        # Verificar se é um arquivo de texto válido
        try:
            csv_file.seek(0)
            # Tentar diferentes encodings
            sample = None
            for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
                try:
                    csv_file.seek(0)
                    sample = csv_file.read(1024).decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if not sample:
                raise forms.ValidationError("Não foi possível decodificar o arquivo. Verifique a codificação.")
            
            csv_file.seek(0)
            
            # Verificar se tem conteúdo CSV válido (pelo menos vírgulas ou ponto e vírgula)
            if ';' not in sample and ',' not in sample:
                raise forms.ValidationError("Arquivo não parece ser um CSV válido (sem delimitadores)")
            
            # Verificação mais flexível dos cabeçalhos
            sample_lower = sample.lower()
            required_patterns = ['nome', 'fórmula', 'peso', 'concentração']
            found_patterns = sum(1 for pattern in required_patterns if pattern in sample_lower)
            
            if found_patterns < 2:  # Pelo menos 2 dos 4 padrões obrigatórios
                raise forms.ValidationError(
                    f"CSV deve conter pelo menos campos relacionados a: nome, fórmula, peso molecular, concentração. "
                    f"Encontrados apenas {found_patterns} padrões reconhecidos."
                )
                
        except UnicodeDecodeError:
            raise forms.ValidationError("Arquivo deve estar codificado em UTF-8, Latin-1 ou Windows-1252")
        except Exception as e:
            # Debug: mostrar erro específico
            print(f"DEBUG: Erro na validação CSV: {str(e)}")
            raise forms.ValidationError(f"Erro ao validar CSV: {str(e)}")
        
        return csv_file
    
class SimpleCSVImportForm(forms.Form):
    """Formulário simplificado para debug"""
    csv_file = forms.FileField(
        label='Arquivo CSV',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv,.txt'
        }),
        help_text='Selecione um arquivo CSV'
    )
    
    def clean_csv_file(self):
        csv_file = self.cleaned_data['csv_file']
        print(f"DEBUG: Validando arquivo: {csv_file.name}, tamanho: {csv_file.size}")
        
        # Validação mínima
        if csv_file.size > 10 * 1024 * 1024:  # 10MB
            raise forms.ValidationError("Arquivo muito grande")
        
        return csv_file
    
class SimulationRunForm(forms.ModelForm):
    initial_concentrations = forms.JSONField(
        widget=forms.HiddenInput(),
        required=False
    )
    
    class Meta:
        model = SimulationRun
        fields = ['name', 'template', 'time_span', 'time_points']
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome da simulação'
            }),
            'template': forms.Select(attrs={
                'class': 'form-select'
            }),
            'time_span': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'min': '0.1',
                'max': '1000'
            }),
            'time_points': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '10',
                'max': '1000',
                'value': '100'
            })
        }
        
        labels = {
            'name': 'Nome da Simulação',
            'template': 'Template de Reação',
            'time_span': 'Tempo de Simulação (s)',
            'time_points': 'Pontos Temporais'
        }

    def __init__(self, *args, **kwargs):
        template = kwargs.pop('template', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar apenas templates ativos
        self.fields['template'].queryset = ReactionTemplate.objects.filter(is_active=True)
        
        # Se template específico fornecido, definir como padrão
        if template:
            self.fields['template'].initial = template
            self.fields['name'].initial = f'Simulação {template.name}'

        if template and template.reactants.exists():
            reactants = template.reactants.all()
            
            for species in reactants:
                field_name = f'initial_concentration_{species.pk}'
                initial_value = species.default_concentration
                
                # ✅ Garantir que o campo não existe antes
                if field_name not in self.fields:
                    self.fields[field_name] = forms.FloatField(
                        label=f"{species.name} ({species.formula})",
                        initial=initial_value,
                        min_value=0.0001,
                        max_value=100.0,
                        widget=forms.NumberInput(attrs={
                            'class': 'form-control',
                            'step': '0.0001',
                            'placeholder': f'{initial_value:.4f}'
                        })
                    )

        print("DEBUG: Campos criados no form:")
        for field_name in self.fields:
            if field_name.startswith('initial_concentration_'):
                print(f"  - {field_name}")
    
    def clean_initial_concentrations(self):
        concentrations = self.cleaned_data.get('initial_concentrations')
        
        if not concentrations:
            # Será preenchido via JavaScript no frontend
            return {}
        
        # Validar que todas as concentrações são positivas
        for species_id, conc in concentrations.items():
            if float(conc) < 0:
                raise forms.ValidationError(f'Concentração deve ser positiva para espécie {species_id}')
        
        return concentrations    
    
