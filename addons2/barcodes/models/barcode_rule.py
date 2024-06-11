import re

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class BarcodeRule(models.Model):
    _name = 'barcode.rule'
    _description = 'Barcode Rule'
    _order = 'sequence asc, id'

    name = fields.Char(string='Rule Name', required=True, help='An internal identification for this barcode nomenclature rule')
    barcode_nomenclature_id = fields.Many2one('barcode.nomenclature', string='Barcode Nomenclature')
    sequence = fields.Integer(string='Sequence', help='Used to order rules such that rules with a smaller sequence match first')
    encoding = fields.Selection(
        string='Encoding', required=True, default='any', selection=[
            ('any', 'Any'),
            ('ean13', 'EAN-13'),
            ('ean8', 'EAN-8'),
            ('upca', 'UPC-A'),
        ], help='This rule will apply only if the barcode is encoded with the specified encoding')
    type = fields.Selection(
        string='Type', required=True, selection=[
            ('alias', 'Alias'),
            ('product', 'Unit Product'),
        ], default='product')
    pattern = fields.Char(string='Barcode Pattern', help="The barcode matching pattern", required=True, default='.*')
    alias = fields.Char(string='Alias', default='0', help='The matched pattern will alias to this barcode', required=True)

    @api.constrains('pattern')
    def _check_pattern(self):
        for rule in self:
            p = rule.pattern.replace('\\\\', 'X').replace('\\{', 'X').replace('\\}', 'X')
            findall = re.findall("[{]|[}]", p)  # p does not contain escaped { or }
            if len(findall) == 2:
                if not re.search("[{][N]*[D]*[}]", p):
                    raise ValidationError(_("There is a syntax error in the barcode pattern %(pattern)s: braces can only contain N's followed by D's.", pattern=rule.pattern))
                elif re.search("[{][}]", p):
                    raise ValidationError(_("There is a syntax error in the barcode pattern %(pattern)s: empty braces.", pattern=rule.pattern))
            elif len(findall) != 0:
                raise ValidationError(_("There is a syntax error in the barcode pattern %(pattern)s: a rule can only contain one pair of braces.", pattern=rule.pattern))
            elif p == '*':
                raise ValidationError(_(" '*' is not a valid Regex Barcode Pattern. Did you mean '.*'?"))
