from django import forms
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
            'reactants': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'size': '5'
            }),
            'products': forms.SelectMultiple(attrs={
                'class': 'form-select', 
                'size': '5'
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
        # Filtrar apenas espécies que podem ser reagentes/produtos
        self.fields['reactants'].queryset = Species.objects.filter(
            simulation_role__in=['reactant', 'product', 'intermediate']
        ).order_by('name')
        
        self.fields['products'].queryset = Species.objects.filter(
            simulation_role__in=['product', 'reactant', 'intermediate']  
        ).order_by('name')

    def clean(self):
        cleaned_data = super().clean()
        reactants = cleaned_data.get('reactants')
        products = cleaned_data.get('products')
        
        # Validar que há pelo menos 1 reagente e 1 produto
        if reactants and len(reactants) < 1:
            raise forms.ValidationError("Selecione pelo menos 1 reagente.")
            
        if products and len(products) < 1:
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