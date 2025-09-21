import csv
import io
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from .models import ReactionTemplate, Species
from .forms import ReactionTemplateForm, SpeciesForm, SpeciesCSVImportForm

# Create your views here.

def reaction_template_list(request):
    """Lista todos os templates de reação com busca e paginação"""
    templates = ReactionTemplate.objects.filter(is_active=True).select_related('created_by')
    
    # Busca
    search = request.GET.get('search')
    if search:
        templates = templates.filter(
            Q(name__icontains=search) | 
            Q(description__icontains=search)
        )
    
    # Filtro por ordem de reação
    order = request.GET.get('order')
    if order:
        templates = templates.filter(reaction_order=order)
    
    # Paginação
    paginator = Paginator(templates, 10)
    page_number = request.GET.get('page')
    templates = paginator.get_page(page_number)
    
    context = {
        'templates': templates,
        'search': search,
        'order': order,
        'order_choices': ReactionTemplate.OrderChoices.choices,
    }
    return render(request, 'chemical_simulator/reaction_template_list.html', context)


def reaction_template_detail(request, pk):
    """Detalhes de um template específico"""
    template = get_object_or_404(ReactionTemplate, pk=pk)
    
    context = {
        'template': template,
        'reactants': template.reactants.all(),
        'products': template.products.all(),
    }
    return render(request, 'chemical_simulator/reaction_template_detail.html', context)


@login_required
def reaction_template_create(request):
    """Criar novo template de reação"""
    if request.method == 'POST':
        form = ReactionTemplateForm(request.POST)
        if form.is_valid():
            template = form.save(commit=False)
            template.created_by = request.user
            template.save()
            form.save_m2m()  # Salvar relações many-to-many
            messages.success(request, f'Template "{template.name}" criado com sucesso!')
            return redirect('reaction_template_detail', pk=template.pk)
    else:
        form = ReactionTemplateForm()
    
    return render(request, 'chemical_simulator/reaction_template_form.html', {
        'form': form,
        'title': 'Criar Template de Reação'
    })


@login_required
def reaction_template_update(request, pk):
    """Editar template de reação existente"""
    template = get_object_or_404(ReactionTemplate, pk=pk)
    
    # Verificar permissões (só o criador ou admin pode editar)
    if template.created_by != request.user and not request.user.is_staff:
        messages.error(request, 'Não tens permissão para editar este template.')
        return redirect('reaction_template_detail', pk=pk)
    
    if request.method == 'POST':
        form = ReactionTemplateForm(request.POST, instance=template)
        if form.is_valid():
            form.save()
            messages.success(request, f'Template "{template.name}" atualizado com sucesso!')
            return redirect('reaction_template_detail', pk=template.pk)
    else:
        form = ReactionTemplateForm(instance=template)
    
    return render(request, 'chemical_simulator/reaction_template_form.html', {
        'form': form,
        'template': template,
        'title': f'Editar: {template.name}'
    })


@login_required
def reaction_template_delete(request, pk):
    """Deletar template de reação (soft delete)"""
    template = get_object_or_404(ReactionTemplate, pk=pk)
    
    # Verificar permissões
    if template.created_by != request.user and not request.user.is_staff:
        messages.error(request, 'Não tens permissão para eliminar este template.')
        return redirect('reaction_template_detail', pk=pk)
    
    if request.method == 'POST':
        template.is_active = False
        template.save()
        messages.success(request, f'Template "{template.name}" eliminado com sucesso!')
        return redirect('reaction_template_list')
    
    return render(request, 'chemical_simulator/reaction_template_confirm_delete.html', {
        'template': template
    })

def species_list(request):
    """Lista todas as espécies químicas com busca e filtros"""
    species = Species.objects.all().order_by('name')
    
    # Busca
    search = request.GET.get('search')
    if search:
        species = species.filter(
            Q(name__icontains=search) | 
            Q(formula__icontains=search) |
            Q(cas_number__icontains=search)
        )
    
    # Filtro por papel na simulação
    role = request.GET.get('role')
    if role:
        species = species.filter(simulation_role=role)
    
    # Filtro por estado físico
    physical_state = request.GET.get('physical_state')
    if physical_state:
        species = species.filter(physical_state=physical_state)
    
    # Paginação
    paginator = Paginator(species, 12)
    page_number = request.GET.get('page')
    species = paginator.get_page(page_number)
    
    context = {
        'species': species,
        'search': search,
        'role': role,
        'physical_state': physical_state,
        'role_choices': Species.RoleChoices.choices,
        'state_choices': Species.PhysicalStateChoices.choices,
    }
    return render(request, 'chemical_simulator/species_list.html', context)


def species_detail(request, pk):
    """Detalhes de uma espécie específica"""
    species = get_object_or_404(Species, pk=pk)
    
    # Buscar reações onde esta espécie participa
    reactions_as_reactant = species.reactions_as_reactant.filter(is_active=True)
    reactions_as_product = species.reactions_as_product.filter(is_active=True)
    
    context = {
        'species': species,
        'reactions_as_reactant': reactions_as_reactant,
        'reactions_as_product': reactions_as_product,
    }
    return render(request, 'chemical_simulator/species_detail.html', context)


@login_required
def species_create(request):
    """Criar nova espécie química"""
    if request.method == 'POST':
        form = SpeciesForm(request.POST)
        if form.is_valid():
            species = form.save()
            messages.success(request, f'Espécie "{species.name}" criada com sucesso!')
            return redirect('species_detail', pk=species.pk)
    else:
        form = SpeciesForm()
    
    return render(request, 'chemical_simulator/species_form.html', {
        'form': form,
        'title': 'Criar Espécie Química'
    })


@login_required
def species_update(request, pk):
    """Editar espécie química existente"""
    species = get_object_or_404(Species, pk=pk)
    
    if request.method == 'POST':
        form = SpeciesForm(request.POST, instance=species)
        if form.is_valid():
            form.save()
            messages.success(request, f'Espécie "{species.name}" atualizada com sucesso!')
            return redirect('species_detail', pk=species.pk)
    else:
        form = SpeciesForm(instance=species)
    
    return render(request, 'chemical_simulator/species_form.html', {
        'form': form,
        'species': species,
        'title': f'Editar: {species.name}'
    })


@login_required
def species_delete(request, pk):
    """Deletar espécie química"""
    species = get_object_or_404(Species, pk=pk)
    
    if request.method == 'POST':
        # Verificar se a espécie está sendo usada em templates
        reactions_count = (
            species.reactions_as_reactant.filter(is_active=True).count() +
            species.reactions_as_product.filter(is_active=True).count()
        )
        
        if reactions_count > 0:
            messages.error(
                request, 
                f'Não é possível eliminar "{species.name}" pois está sendo usada em {reactions_count} template(s) de reação.'
            )
            return redirect('species_detail', pk=pk)
        
        species_name = species.name
        species.delete()
        messages.success(request, f'Espécie "{species_name}" eliminada com sucesso!')
        return redirect('species_list')
    
    return render(request, 'chemical_simulator/species_confirm_delete.html', {
        'species': species
    })


@login_required
def species_csv_import(request):
    """Importar espécies via CSV"""
    if request.method == 'POST':
        form = SpeciesCSVImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            
            try:
                # Ler arquivo CSV
                file_data = csv_file.read().decode('utf-8')
                csv_data = csv.DictReader(io.StringIO(file_data))
                
                created_count = 0
                error_count = 0
                errors = []
                
                for row_num, row in enumerate(csv_data, start=2):
                    try:
                        # Validar campos obrigatórios
                        if not all([row.get('name'), row.get('formula'), row.get('molecular_weight'), row.get('default_concentration')]):
                            errors.append(f"Linha {row_num}: Campos obrigatórios em falta")
                            error_count += 1
                            continue
                        
                        # Verificar se já existe
                        if Species.objects.filter(name=row['name']).exists():
                            errors.append(f"Linha {row_num}: Espécie '{row['name']}' já existe")
                            error_count += 1
                            continue
                        
                        # Criar espécie
                        species_data = {
                            'name': row['name'].strip(),
                            'formula': row['formula'].strip(),
                            'molecular_weight': float(row['molecular_weight']),
                            'default_concentration': float(row['default_concentration']),
                            'density': float(row.get('density', 0)) if row.get('density') else None,
                            'physical_state': row.get('physical_state', 'aqueous'),
                            'simulation_role': row.get('simulation_role', 'reactant'),
                            'color': row.get('color', 'incolor'),
                            'transparency': row.get('transparency', 'transparent'),
                            'description': row.get('description', ''),
                            'cas_number': row.get('cas_number', ''),
                        }
                        
                        Species.objects.create(**species_data)
                        created_count += 1
                        
                    except (ValueError, TypeError) as e:
                        errors.append(f"Linha {row_num}: Erro de dados - {str(e)}")
                        error_count += 1
                    except Exception as e:
                        errors.append(f"Linha {row_num}: Erro inesperado - {str(e)}")
                        error_count += 1
                
                # Mensagens de resultado
                if created_count > 0:
                    messages.success(request, f'{created_count} espécie(s) importada(s) com sucesso!')
                
                if error_count > 0:
                    messages.warning(request, f'{error_count} erro(s) encontrado(s).')
                    for error in errors[:5]:  # Mostrar apenas os primeiros 5 erros
                        messages.error(request, error)
                    if len(errors) > 5:
                        messages.info(request, f'... e mais {len(errors) - 5} erro(s).')
                
                if created_count > 0:
                    return redirect('species_list')
                    
            except Exception as e:
                messages.error(request, f'Erro ao processar arquivo CSV: {str(e)}')
    else:
        form = SpeciesCSVImportForm()
    
    return render(request, 'chemical_simulator/species_csv_import.html', {
        'form': form,
        'title': 'Importar Espécies via CSV'
    })


def species_csv_template(request):
    """Download template CSV para importação"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="species_template.csv"'
    
    writer = csv.writer(response)
    
    # Cabeçalho
    writer.writerow([
        'name', 'formula', 'molecular_weight', 'default_concentration',
        'density', 'physical_state', 'simulation_role', 'color', 
        'transparency', 'description', 'cas_number'
    ])
    
    # Exemplos
    writer.writerow([
        'Água', 'H2O', '18.015', '55.56', '1.0', 'liquid', 'solvent', 
        'incolor', 'transparent', 'Água destilada', '7732-18-5'
    ])
    writer.writerow([
        'Cloreto de Sódio', 'NaCl', '58.443', '1.0', '2.16', 'solid', 
        'reactant', 'white', 'opaque', 'Sal comum', '7647-14-5'
    ])
    writer.writerow([
        'Ácido Clorídrico', 'HCl', '36.458', '0.1', '1.18', 'aqueous', 
        'reactant', 'incolor', 'transparent', 'Ácido forte', '7647-01-0'
    ])
    
    return response

def simulation_list(request):
    """Placeholder view para simulations (será implementada depois)"""
    return render(request, 'chemical_simulator/placeholder.html', {
        'title': 'Simulações - Em desenvolvimento'
    })