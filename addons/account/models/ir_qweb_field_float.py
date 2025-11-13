from odoo import api, models


class IrQwebFieldFloat(models.AbstractModel):
    _name = 'ir.qweb.field.float'
    _inherit = ['ir.qweb.field.float']

    @api.model
    def value_to_html(self, value, options):
        if options['expression'] == 'line.price_unit':
            min_precision = self.env['decimal.precision'].precision_get('Product Price')
            value_str = '%f' % value
            _int_part, dec_part = value_str.split('.')
            if len(dec_part.rstrip('0')) < min_precision:
                options['precision'] = min_precision

        return super().value_to_html(value, options)
