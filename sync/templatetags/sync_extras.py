from django import template

register = template.Library()

@register.filter
def get_status(grid, user_id):
    return grid.get(user_id, {})

@register.simple_tag
def get_avail(grid, user_id, date):
    return grid.get(user_id, {}).get(str(date), '')