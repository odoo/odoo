# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import groupby
from openerp import fields, models


def grouplines(ordered_lines, sortkey):
    """Return lines from a specified invoice or sale order grouped by category"""
    grouped_lines = []
    for key, valuesiter in groupby(ordered_lines, sortkey):
        group = {}
        group['category'] = key
        group['lines'] = list(v for v in valuesiter)

        if 'subtotal' in key and key.subtotal is True:
            group['subtotal'] = sum(line.price_subtotal for line in group['lines'])
        grouped_lines.append(group)

    return grouped_lines


class SaleLayoutCategory(models.Model):
    _name = 'sale_layout.category'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(required=True, default=10)
    subtotal = fields.Boolean(string='Add subtotal', default=True)
    separator = fields.Boolean(string='Add separator', default=True)
    pagebreak = fields.Boolean(string='Add pagebreak')
