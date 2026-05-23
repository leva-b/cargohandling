from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django import template

register = template.Library()


@register.filter
def as_timezone(value, timezone_name):
    if not value:
        return ''
    try:
        return value.astimezone(ZoneInfo(timezone_name))
    except ZoneInfoNotFoundError:
        return value
