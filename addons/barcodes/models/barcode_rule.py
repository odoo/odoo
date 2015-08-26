# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re

from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import ValidationError

_logger = logging.getLogger(__name__)


ENCODINGS = [
    ('any','Any'),
    ('ean13','EAN-13'),
    ('ean8','EAN-8'),
    ('upca','UPC-A'),
]


class BarcodeRule(models.Model):
    _name = 'barcode.rule'
    _order = 'sequence asc'

    name = fields.Char('Rule Name', size=32, required=True, help='An internal identification for this barcode nomenclature rule')
    barcode_nomenclature_id = fields.Many2one('barcode.nomenclature', 'Barcode Nomenclature')
    sequence = fields.Integer('Sequence', help='Used to order rules such that rules with a smaller sequence match first')
    encoding = fields.Selection(ENCODINGS, 'Encoding', required=True, default='any', help='This rule will apply only if the barcode is encoded with the specified encoding')
    types = fields.Selection('_get_type_selection', 'Type', required=True, default='product', oldname='type')
    pattern = fields.Char('Barcode Pattern', size=32, help="The barcode matching pattern", required=True, default='.*')
    alias = fields.Char('Alias', size=32, default='0', help='The matched pattern will alias to this barcode', required=True)

    @api.model
    def _encoding_selection_list(self):
        return [
                ('any', 'Any'),
                ('ean13', 'EAN-13'),
                ('ean8', 'EAN-8'),
                ('upca', 'UPC-A'),
        ]

    @api.model
    def _get_type_selection(self):
        return [('alias', 'Alias'), ('product', 'Unit Product')]

    @api.one
    @api.constrains('pattern')
    def _check_pattern(self):
        p = self.pattern.replace("\\\\", "X").replace("\{", "X").replace("\}", "X")
        findall = re.findall("[{]|[}]", p) # p does not contain escaped { or }
        if len(findall) == 2: 
            if not re.search("[{][N]*[D]*[}]", p):
                raise ValidationError(_("There is a syntax error in the barcode pattern ") + self.pattern + _(": braces can only contain N's followed by D's."))
            elif re.search("[{][}]", p):
                raise ValidationError(_("There is a syntax error in the barcode pattern ") + self.pattern + _(": empty braces."))
        elif len(findall) != 0:
            raise ValidationError(_("There is a syntax error in the barcode pattern ") + self.pattern + _(": a rule can only contain one pair of braces."))
        elif p == '*':
            raise ValidationError(_(" '*' is not a valid Regex Barcode Pattern. Did you mean '.*' ?"))
