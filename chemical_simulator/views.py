import csv
import io
import traceback
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from .models import ReactionTemplate, Species, SimulationRun
from .forms import ReactionTemplateForm, SpeciesForm, SpeciesCSVImportForm, TemplateSpeciesAssociationForm, SimulationRunForm
from .simulation_engine import create_and_run_simulation, SimulationError

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
        print("\n=== DEBUG POST ===")
        print("Reactants recebidos:", request.POST.getlist('reactants'))
        print("Products recebidos:", request.POST.getlist('products'))
        print("Todos os dados POST:", dict(request.POST))
        print("==================\n")

        form = ReactionTemplateForm(request.POST)
        print("Formulário é válido?", form.is_valid())

        if not form.is_valid():
            print("Erros do formulário (detalhados):")
            for field, errors in form.errors.items():
                print(f"  {field}: {list(errors)}")
            
            # Debug: verificar querysets
            print("IDs disponíveis para reactants:", list(form.fields['reactants'].queryset.values_list('id', flat=True)))
            print("IDs disponíveis para products:", list(form.fields['products'].queryset.values_list('id', flat=True)))
        
        if form.is_valid():
            template = form.save(commit=False)
            template.created_by = request.user
            template.save()
            form.save_m2m()  # Salvar relações many-to-many
            messages.success(request, f'Template "{template.name}" criado com sucesso!')
            print(f"Template salvo com PK: {template.pk}")
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
    """Importar espécies via CSV com debug melhorado"""
    if request.method == 'POST':
        form = SpeciesCSVImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            
            try:
                # Debug: mostrar info do arquivo
                print(f"DEBUG: Arquivo: {csv_file.name}, Tamanho: {csv_file.size} bytes")
                
                # Ler arquivo CSV
                csv_file.seek(0)
                file_data = csv_file.read().decode('utf-8-sig')  # utf-8-sig para BOM
                print(f"DEBUG: Primeiros 500 chars: {file_data[:500]}")
                
                # Detectar delimitador
                import csv
                sniffer = csv.Sniffer()
                try:
                    delimiter = sniffer.sniff(file_data[:1024]).delimiter
                    print(f"DEBUG: Delimitador detectado: '{delimiter}'")
                except:
                    delimiter = ';'  # Padrão europeu
                    print(f"DEBUG: Usando delimitador padrão: '{delimiter}'")
                
                csv_data = csv.DictReader(io.StringIO(file_data), delimiter=delimiter)
                
                # Debug: mostrar cabeçalhos
                fieldnames = csv_data.fieldnames
                print(f"DEBUG: Cabeçalhos encontrados: {fieldnames}")
                
                created_count = 0
                error_count = 0
                errors = []

                # Mapeamentos melhorados
                physical_state_map = {
                    'líquido': 'liquid',
                    'sólido': 'solid', 
                    'gasoso': 'gas',
                    'aquoso': 'aqueous',
                    'liquid': 'liquid',
                    'solid': 'solid',
                    'gas': 'gas',
                    'aqueous': 'aqueous'
                }
                
                role_map = {
                    'reagente': 'reactant',
                    'produto': 'product',
                    'catalisador': 'catalyst',
                    'solvente': 'solvent',
                    'intermediário': 'intermediate',
                    'reactant': 'reactant',
                    'product': 'product',
                    'catalyst': 'catalyst',
                    'solvent': 'solvent',
                    'intermediate': 'intermediate'
                }
                
                color_map = {
                    'branco': 'white',
                    'azul': 'blue',
                    'verde': 'green',
                    'amarelo': 'yellow',
                    'vermelho': 'red',
                    'castanho': 'brown',
                    'preto': 'black',
                    'roxo': 'purple',
                    'laranja': 'orange',
                    'incolor': 'incolor',
                    'white': 'white',
                    'blue': 'blue',
                    'green': 'green',
                    'yellow': 'yellow',
                    'red': 'red',
                    'brown': 'brown',
                    'black': 'black',
                    'purple': 'purple',
                    'orange': 'orange'
                }
                
                transparency_map = {
                    'transparente': 'transparent',
                    'translúcido': 'translucent',
                    'opaco': 'opaque',
                    'transparent': 'transparent',
                    'translucent': 'translucent',
                    'opaque': 'opaque'
                }
                
                for row_num, row in enumerate(csv_data, start=2):
                    try:
                        print(f"DEBUG: Linha {row_num}: {dict(row)}")
                        
                        # Função para encontrar campo por similiaridade
                        def find_field(target_names, row_dict):
                            for target in target_names:
                                for key in row_dict.keys():
                                    if target.lower() in key.lower():
                                        return row_dict[key]
                            return None
                        
                        # Mapear campos de forma flexível
                        name = find_field(['nome', 'name'], row)
                        formula = find_field(['fórmula', 'formula'], row)
                        molecular_weight = find_field(['peso molecular', 'molecular_weight'], row)
                        default_concentration = find_field(['concentração', 'concentration'], row)
                        density = find_field(['densidade', 'density'], row)
                        physical_state = find_field(['estado físico', 'physical_state'], row)
                        simulation_role = find_field(['papel', 'role', 'simulation_role'], row)
                        color = find_field(['cor', 'color'], row)
                        transparency = find_field(['transparência', 'transparency'], row)
                        description = find_field(['descrição', 'description'], row)
                        cas_number = find_field(['cas', 'número cas'], row)
                        
                        print(f"DEBUG: Campos mapeados - name: {name}, formula: {formula}")
                        
                        # Validar campos obrigatórios
                        if not all([name, formula, molecular_weight, default_concentration]):
                            errors.append(f"Linha {row_num}: Campos obrigatórios em falta - name: {name}, formula: {formula}, weight: {molecular_weight}, conc: {default_concentration}")
                            error_count += 1
                            continue
                        
                        # Verificar se já existe
                        if Species.objects.filter(name=name.strip()).exists():
                            errors.append(f"Linha {row_num}: Espécie '{name}' já existe")
                            error_count += 1
                            continue
                        
                        # Processar números (trocar vírgula por ponto)
                        def clean_number(value):
                            if not value:
                                return None
                            return float(str(value).replace(',', '.').strip())
                        
                        # Criar dados da espécie
                        species_data = {
                            'name': name.strip(),
                            'formula': formula.strip(),
                            'molecular_weight': clean_number(molecular_weight),
                            'default_concentration': clean_number(default_concentration),
                            'density': clean_number(density) if density else None,
                            'physical_state': physical_state_map.get(physical_state.lower().strip() if physical_state else '', 'aqueous'),
                            'simulation_role': role_map.get(simulation_role.lower().strip() if simulation_role else '', 'reactant'),
                            'color': color_map.get(color.lower().strip() if color else '', 'incolor'),
                            'transparency': transparency_map.get(transparency.lower().strip() if transparency else '', 'transparent'),
                            'description': description.strip() if description else '',
                            'cas_number': cas_number.strip() if cas_number else '',
                        }
                        
                        print(f"DEBUG: Dados finais: {species_data}")
                        
                        Species.objects.create(**species_data)
                        created_count += 1
                        print(f"DEBUG: Espécie '{name}' criada com sucesso")
                        
                    except Exception as e:
                        error_msg = f"Linha {row_num}: Erro - {str(e)}"
                        errors.append(error_msg)
                        print(f"DEBUG: {error_msg}")
                        error_count += 1
                
                # Mensagens de resultado
                if created_count > 0:
                    messages.success(request, f'{created_count} espécie(s) importada(s) com sucesso!')
                
                if error_count > 0:
                    messages.warning(request, f'{error_count} erro(s) encontrado(s).')
                    for error in errors[:5]:
                        messages.error(request, error)
                    if len(errors) > 5:
                        messages.info(request, f'... e mais {len(errors) - 5} erro(s).')
                
                if created_count > 0:
                    return redirect('species_list')
                    
            except Exception as e:
                error_msg = f'Erro ao processar arquivo CSV: {str(e)}'
                messages.error(request, error_msg)
                print(f"DEBUG: {error_msg}")
                import traceback
                print(f"DEBUG: Traceback: {traceback.format_exc()}")
        else:
            print(f"DEBUG: Formulário inválido: {form.errors}")
            messages.error(request, f"Erro no formulário: {form.errors}")
    else:
        form = SpeciesCSVImportForm()
    
    return render(request, 'chemical_simulator/species_csv_import.html', {
        'form': form,
        'title': 'Importar Espécies via CSV'
    })

def species_csv_template(request):
    """Download template CSV para importação"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="especies_template.csv"'
    
    writer = csv.writer(response)
    
    # Cabeçalho em português (igual ao teu arquivo)
    writer.writerow([
        'Nome', 'Fórmula Química', 'Peso Molecular (g/mol)', 'Densidade (g/cm³) (a 25ºC)',
        'Estado Físico (25°C)', 'Concentração Padrão Sugerida (mol·L⁻¹)', 'Papel na Simulação',
        'Cor', 'Transparência', 'Descrição', 'Número CAS'
    ])
    
    # Exemplos
    writer.writerow([
        'Água', 'H2O', '18,015', '0,997', 'líquido', '55,56', 'solvente', 
        'incolor', 'transparente', 'Água destilada', '7732-18-5'
    ])
    writer.writerow([
        'Cloreto de Sódio', 'NaCl', '58,443', '2,165', 'sólido', '0,154', 
        'reagente', 'branco', 'transparente', 'Sal comum', '7647-14-5'
    ])
    
    return response


def simulation_list(request):
    """Placeholder view para simulations (será implementada depois)"""
    return render(request, 'chemical_simulator/placeholder.html', {
        'title': 'Simulações - Em desenvolvimento'
    })


# Adicionar ao chemical_simulator/views.py

@login_required
def template_species_manage(request, pk):
    """Interface visual para gerir associações species-template"""
    template = get_object_or_404(ReactionTemplate, pk=pk)
    
    # Verificar permissões
    if template.created_by != request.user and not request.user.is_staff:
        messages.error(request, 'Não tens permissão para editar este template.')
        return redirect('reaction_template_detail', pk=pk)
    
    if request.method == 'POST':
        form = TemplateSpeciesAssociationForm(template=template, data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Associações de espécies atualizadas com sucesso!')
            return redirect('reaction_template_detail', pk=template.pk)
    else:
        form = TemplateSpeciesAssociationForm(template=template)
    
    # Organizar espécies por categoria para melhor visualização
    species_by_role = {}
    for role_key, role_label in Species.RoleChoices.choices:
        species_by_role[role_key] = {
            'label': role_label,
            'species': Species.objects.filter(simulation_role=role_key).order_by('name')
        }
    
    context = {
        'template': template,
        'form': form,
        'species_by_role': species_by_role,
        'title': f'Gerir Espécies: {template.name}'
    }
    return render(request, 'chemical_simulator/template_species_manage.html', context)


def reaction_equation_preview(request, pk):
    """API endpoint para preview da equação química"""
    template = get_object_or_404(ReactionTemplate, pk=pk)
    
    # Construir equação química
    reactants = list(template.reactants.all())
    products = list(template.products.all())
    
    equation_data = {
        'reactants': [{'name': r.name, 'formula': r.formula} for r in reactants],
        'products': [{'name': p.name, 'formula': p.formula} for p in products],
        'equation_text': ' + '.join([r.formula for r in reactants]) + ' → ' + ' + '.join([p.formula for p in products])
    }
    
    return JsonResponse(equation_data)


@login_required
def species_quick_add(request):
    """Modal para adicionar espécie rapidamente durante criação de template"""
    if request.method == 'POST':
        form = SpeciesForm(request.POST)
        if form.is_valid():
            species = form.save()
            # Retornar dados da espécie para AJAX
            return JsonResponse({
                'success': True,
                'species': {
                    'id': species.pk,
                    'name': species.name,
                    'formula': species.formula,
                    'role': species.simulation_role
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
    
    form = SpeciesForm()
    return render(request, 'chemical_simulator/species_quick_add_modal.html', {
        'form': form
    })


def template_species_suggestions(request):
    """API para sugerir espécies baseado no tipo de reação"""
    reaction_type = request.GET.get('type', '')
    query = request.GET.get('q', '')
    
    suggestions = []
    
    # Filtrar espécies baseado no tipo de busca
    species_qs = Species.objects.all()
    
    if query:
        species_qs = species_qs.filter(
            Q(name__icontains=query) | 
            Q(formula__icontains=query)
        )
    
    # Sugestões baseadas no tipo de reação
    if reaction_type == 'neutralization':
        # Sugerir ácidos e bases
        acid_base_species = species_qs.filter(
            Q(description__icontains='ácido') | 
            Q(description__icontains='base') |
            Q(name__icontains='ácido') |
            Q(name__icontains='hidróxido')
        )
        suggestions.extend(acid_base_species)
    
    elif reaction_type == 'precipitation':
        # Sugerir sais
        salt_species = species_qs.filter(
            Q(simulation_role='reactant') |
            Q(name__icontains='cloreto') |
            Q(name__icontains='sulfato')
        )
        suggestions.extend(salt_species)
    
    # Limitar a 10 sugestões
    suggestions = suggestions[:10]
    
    return JsonResponse({
        'suggestions': [{
            'id': s.pk,
            'name': s.name,
            'formula': s.formula,
            'role': s.get_simulation_role_display(),
            'concentration': s.default_concentration
        } for s in suggestions]
    })

def simulation_list(request):
    """Lista de simulações do utilizador"""
    simulations = SimulationRun.objects.all().select_related('template', 'created_by').order_by('-created_at')
    
    # Filtrar por utilizador se não for staff
    if not request.user.is_staff:
        simulations = simulations.filter(created_by=request.user)
    
    # Filtros
    status = request.GET.get('status')
    if status:
        simulations = simulations.filter(status=status)
    
    template_id = request.GET.get('template')
    if template_id:
        simulations = simulations.filter(template_id=template_id)
    
    # Paginação
    paginator = Paginator(simulations, 15)
    page_number = request.GET.get('page')
    simulations = paginator.get_page(page_number)
    
    context = {
        'simulations': simulations,
        'status': status,
        'template_id': template_id,
        'status_choices': SimulationRun.StatusChoices.choices,
        'templates': ReactionTemplate.objects.filter(is_active=True)
    }
    return render(request, 'chemical_simulator/simulation_list.html', context)


@login_required
def simulation_create(request, template_pk=None):
    """Criar nova simulação"""
    template = None
    if template_pk:
        template = get_object_or_404(ReactionTemplate, pk=template_pk, is_active=True)
    
    if request.method == 'POST':
        form = SimulationRunForm(request.POST, template=template)
        if form.is_valid():
            try:
                # Executar simulação
                simulation_run, error = create_and_run_simulation(
                    template=form.cleaned_data['template'],
                    initial_concentrations=form.cleaned_data['initial_concentrations'],
                    time_span=form.cleaned_data['time_span'],
                    time_points=form.cleaned_data['time_points'],
                    user=request.user
                )
                
                if error:
                    messages.error(request, f'Erro na simulação: {error}')
                else:
                    messages.success(request, 'Simulação executada com sucesso!')
                    return redirect('simulation_detail', pk=simulation_run.pk)
                    
            except Exception as e:
                messages.error(request, f'Erro inesperado: {str(e)}')
    else:
        form = SimulationRunForm(template=template)
    
    context = {
        'form': form,
        'template': template,
        'title': f'Nova Simulação{" - " + template.name if template else ""}',
        'reaction_order': template.reaction_order if template else None,
        'rate_constant': template.rate_constant if template else None,
        'kinetic_law': template.get_reaction_order_display() if template else None,
    }
    return render(request, 'chemical_simulator/simulation_form.html', context)


def simulation_detail(request, pk):
    """Detalhes da simulação com visualização"""
    simulation = get_object_or_404(SimulationRun, pk=pk)
    
    try:
        resolution = simulation.time_span / simulation.time_points
    except (ZeroDivisionError, TypeError):
        resolution = 0

    # Verificar permissões
    if not request.user.is_staff and simulation.created_by != request.user:
        messages.error(request, 'Não tens permissão para ver esta simulação.')
        return redirect('simulation_list')
    
    context = {
        'simulation': simulation,
        'resolution': resolution,
        'has_results': simulation.results is not None,
        'template': simulation.template
    }
    return render(request, 'chemical_simulator/simulation_detail.html', context)