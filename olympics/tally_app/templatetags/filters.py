from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


@register.filter
def classname(obj):
    return obj.__class__.__name__
