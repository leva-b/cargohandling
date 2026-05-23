import json
import logging
from urllib.error import URLError
from urllib.request import urlopen

logger = logging.getLogger(__name__)


def _get_json(url):
    try:
        with urlopen(url, timeout=4) as response:
            return json.loads(response.read().decode('utf-8'))
    except (OSError, URLError, json.JSONDecodeError) as exc:
        logger.warning('External API request failed: %s', exc)
        return None


def get_world_time(timezone_name='Europe/Minsk'):
    data = _get_json(f'https://worldtimeapi.org/api/timezone/{timezone_name}')
    if not data:
        return {'source': 'WorldTimeAPI', 'available': False}

    return {
        'source': 'WorldTimeAPI',
        'available': True,
        'timezone': data.get('timezone'),
        'datetime': data.get('datetime'),
        'utc_datetime': data.get('utc_datetime'),
    }


def get_usd_byn_rate():
    data = _get_json('https://open.er-api.com/v6/latest/USD')
    rates = data.get('rates', {}) if data else {}
    byn = rates.get('BYN')
    if not byn:
        return {'source': 'open.er-api.com', 'available': False}

    return {
        'source': 'open.er-api.com',
        'available': True,
        'base': 'USD',
        'target': 'BYN',
        'rate': byn,
    }
