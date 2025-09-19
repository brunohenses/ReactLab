from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import ReactionTemplate, Species
from .forms import ReactionTemplateForm

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
    return render(request, 'chemical_simulator/placeholder.html', {'title': 'Species - Em desenvolvimento'})

def simulation_list(request):
    return render(request, 'chemical_simulator/placeholder.html', {'title': 'Simulations - Em desenvolvimento'})    