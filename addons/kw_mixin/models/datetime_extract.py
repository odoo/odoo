import datetime
import logging

from odoo import models

_logger = logging.getLogger(__name__)

DATE_PATTERNS = ['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y', '%d-%m-%Y', '%Y%m%d', ]
DATETIME_PATTERNS = ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S',
                     '%Y-%m-%dT%H:%M:%S%f', ]


def get_date_from_format(date_str, date_patterns=None):
    date_patterns = date_patterns or DATE_PATTERNS
    for pattern in date_patterns:
        try:
            return datetime.datetime.strptime(date_str, pattern).date()
        except Exception as e:
            _logger.debug('%s', e)
    return False


# pylint: disable=R1710
def mining_date(value, silent=False):
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        date = get_date_from_format(value)
        if date:
            return date
        if silent:
            return False
        raise Exception(
            '"value" must be type of date, datetime or date '
            'compatible string')
    if silent:
        return False
    raise Exception(
        '"date" must be type of date, datetime or date '
        'compatible string')


def get_datetime_from_format(date_str, date_patterns=None):
    date_patterns = date_patterns or DATETIME_PATTERNS
    for pattern in date_patterns:
        try:
            return datetime.datetime.strptime(date_str, pattern)
        except Exception as e:
            _logger.debug('%s', e)
    return False


# pylint: disable=R1710
def mining_datetime(value, silent=False):
    if isinstance(value, datetime.datetime):
        return value
    if isinstance(value, datetime.date):
        return datetime.datetime(value.year, value.month, value.day)
    if isinstance(value, str):
        date = get_datetime_from_format(value)
        if date:
            return date
        if silent:
            return False
        raise Exception(
            '"value" must be type of date, datetime or datetime '
            'compatible string')
    if silent:
        return False
    raise Exception(
        '"value" must be type of date, datetime or date '
        'compatible string')


class DatetimeMixin(models.AbstractModel):
    _name = 'kw.datetime.extract.mixin'
    _description = 'Extract date or datetime'

    @staticmethod
    def kw_get_date_from_format(date_str, date_patterns=None):
        return get_date_from_format(date_str, date_patterns)

    @staticmethod
    def kw_mining_date(value, silent=False):
        return mining_date(value, silent)

    @staticmethod
    def kw_get_datetime_from_format(date_str, date_patterns=None):
        return get_datetime_from_format(date_str, date_patterns)

    @staticmethod
    def kw_mining_datetime(value, silent=False):
        return mining_datetime(value, silent)
