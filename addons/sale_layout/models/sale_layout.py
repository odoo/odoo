# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv, fields
from itertools import groupby


def grouplines(self, ordered_lines, sortkey):
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


class SaleLayoutCategory(osv.Model):
    _name = 'sale_layout.category'
    _order = 'sequence, id'
    _columns = {
        'name': fields.char('Name', required=True, translate=True),
        'sequence': fields.integer('Sequence', required=True),
        'subtotal': fields.boolean('Add subtotal'),
        'separator': fields.boolean('Add separator'),
        'pagebreak': fields.boolean('Add pagebreak')
    }

    _defaults = {
        'subtotal': True,
        'separator': True,
        'pagebreak': False,
        'sequence': 10
    }
