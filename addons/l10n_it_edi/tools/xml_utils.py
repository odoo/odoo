# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.addons.base.models.ir_qweb_fields import Markup, nl2br_enclose


def get_text(tree, xpath, many=False):
    texts = [el.text.strip() for el in tree.xpath(xpath) if el.text]
    return texts if many else texts[0] if texts else ''

def get_float(tree, xpath):
    return float(get_text(tree, xpath) or '0')

def get_date(tree, xpath):
    """ Dates in FatturaPA are ISO 8601 date format, pattern '[-]CCYY-MM-DD[Z|(+|-)hh:mm]' """
    if dt := get_datetime(tree, xpath):
        return dt.date()
    return False

def get_datetime(tree, xpath):
    """ Datetimes in FatturaPA are ISO 8601 date format, pattern '[-]CCYY-MM-DDThh:mm:ss[Z|(+|-)hh:mm]'
        Python 3.7 -> 3.11 doesn't support 'Z'.
    """
    if (datetime_str := get_text(tree, xpath)):
        try:
            return datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            pass
    return False

def format_errors(header, errors):
    return Markup('{}<ul class="mb-0">{}</ul>').format(
        nl2br_enclose(header, 'span') if header else '',
        Markup().join(
            nl2br_enclose(' '.join(error.split()), 'li')
            for error in errors
        )
    )
