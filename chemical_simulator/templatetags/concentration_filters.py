# chemical_simulator/templatetags/concentration_filters.py

from django import template

register = template.Library()

@register.filter
def starts_with(value, prefix):
    return str(value).startswith(str(prefix))