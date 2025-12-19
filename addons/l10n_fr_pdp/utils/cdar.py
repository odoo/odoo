from datetime import datetime


def _parse_datetime(date):
    if date is None:
        return None
    return datetime.strptime(date, '%Y%m%d%H%M%S')


def _parse_date(date):
    if date is None:
        return None
    return datetime.strptime(date, '%Y%m%d')


def _parse_datetime_node(node):
    if node is None:
        return None
    issue_date_parser = {
        '102': lambda n: dt.replace(hour=12) if (dt := _parse_date(n)) else None,
        '204': _parse_datetime,
    }.get(node.get('format'), _parse_datetime)
    try:
        return issue_date_parser(node.text)
    except Exception:  # noqa: BLE001
        return None
