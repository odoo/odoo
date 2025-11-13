from odoo import models


class IrQwebFieldFloat(models.AbstractModel):
    _name = 'ir.qweb.field.float'
    _inherit = ['ir.qweb.field.float']

    def record_to_html(self, record, field_name, options):
        if 'precision' not in options and record._name == 'account.move.line' and field_name == 'price_unit':
            value = record.price_unit
            min_precision = self.env['decimal.precision'].precision_get('Product Price')
            value_str = '%f' % value
            _int_part, dec_part = value_str.split('.')
            options['precision'] = max(min_precision, len(dec_part.rstrip('0')))
        return super().record_to_html(record, field_name, options)
