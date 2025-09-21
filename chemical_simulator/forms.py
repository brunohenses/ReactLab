from django import forms
from django.forms.widgets import CheckboxSelectMultiple
from .models import ReactionTemplate, Species

class ReactionTemplateForm(forms.ModelForm):
    class Meta:
        model = ReactionTemplate
        fields = ['name', 'description', 'reaction_order', 'rate_constant', 'reactants', 'products', 'is_active']
        
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
            
            # Usar checkboxes para seleção múltipla de espécies
            'reactants': CheckboxSelectMultiple(attrs={
                'class': 'species-checkbox-list'
            }),
            'products': CheckboxSelectMultiple(attrs={
                'class': 'species-checkbox-list'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
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
        super().__init__(**kwargs)
        
        # Organizar espécies por papel na simulação
        reactant_species = Species.objects.filter(
            simulation_role__in=['reactant', 'intermediate']
        ).order_by('name')
        
        product_species = Species.objects.filter(
            simulation_role__in=['product', 'intermediate']
        ).order_by('name')
        
        # Adicionar todas as espécies como opção (caso user queira escolher diferente do role)
        all_species = Species.objects.all().order_by('name')
        
        self.fields['reactants'].queryset = all_species
        self.fields['products'].queryset = all_species
        
        # Adicionar classes CSS para styling
        self.fields['reactants'].widget.attrs.update({
            'data-role': 'reactants',
            'data-default-filter': 'reactant,intermediate'
        })
        
        self.fields['products'].widget.attrs.update({
            'data-role': 'products', 
            'data-default-filter': 'product,intermediate'
        })

    def clean(self):
        cleaned_data = super().clean()
        reactants = cleaned_data.get('reactants')
        products = cleaned_data.get('products')
        
        # Validar que há pelo menos 1 reagente e 1 produto
        if not reactants or len(reactants) < 1:
            raise forms.ValidationError("Selecione pelo menos 1 reagente.")
            
        if not products or len(products) < 1:
            raise forms.ValidationError("Selecione pelo menos 1 produto.")
            
        # Verificar que reagentes e produtos não se sobrepõem
        if reactants and products:
            overlap = set(reactants) & set(products)
            if overlap:
                species_names = ', '.join([s.name for s in overlap])
                raise forms.ValidationError(
                    f"As seguintes espécies não podem ser reagentes e produtos simultaneamente: {species_names}"
                )
        
        return cleaned_data


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
        if not csv_file.name.endswith('.csv'):
            raise forms.ValidationError("Arquivo deve ter extensão .csv")
        
        # Verificar tamanho (máximo 5MB)
        if csv_file.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Arquivo muito grande. Máximo permitido: 5MB")
        
        # Verificar se é um arquivo de texto válido
        try:
            csv_file.seek(0)
            sample = csv_file.read(1024).decode('utf-8')
            csv_file.seek(0)
            
            # Verificar se tem cabeçalho esperado
            required_headers = ['name', 'formula', 'molecular_weight', 'default_concentration']
            if not all(header in sample.lower() for header in required_headers):
                raise forms.ValidationError(
                    f"CSV deve conter pelo menos os cabeçalhos: {', '.join(required_headers)}"
                )
                
        except UnicodeDecodeError:
            raise forms.ValidationError("Arquivo deve estar codificado em UTF-8")
        except Exception:
            raise forms.ValidationError("Arquivo CSV inválido")
        
        return csv_file