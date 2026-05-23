import calendar
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.utils import timezone


def time_context(request):
    timezone_name = request.GET.get('tz') or request.session.get(
        'user_timezone',
        getattr(settings, 'USER_TIME_ZONE', 'Europe/Minsk'),
    )
    try:
        user_tz = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        timezone_name = getattr(settings, 'USER_TIME_ZONE', 'Europe/Minsk')
        user_tz = ZoneInfo(timezone_name)

    if request.GET.get('tz'):
        request.session['user_timezone'] = timezone_name

    utc_now = timezone.now()
    user_now = utc_now.astimezone(user_tz)
    month_calendar = calendar.TextCalendar(firstweekday=0).formatmonth(
        user_now.year,
        user_now.month,
    )

    return {
        'user_timezone_name': timezone_name,
        'current_user_datetime': user_now,
        'current_utc_datetime': utc_now.astimezone(ZoneInfo('UTC')),
        'current_user_date': user_now.date(),
        'current_utc_date': datetime.now(ZoneInfo('UTC')).date(),
        'text_calendar': month_calendar,
    }
