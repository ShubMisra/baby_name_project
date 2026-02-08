from app.services.muhurat.config.settings import RAHU_KALAM


def is_rahu_kalam(local_dt):
    weekday = local_dt.weekday()
    start, end = RAHU_KALAM.get(weekday, (None, None))

    if start is None:
        return False

    hour = local_dt.hour + local_dt.minute / 60.0
    return start <= hour <= end