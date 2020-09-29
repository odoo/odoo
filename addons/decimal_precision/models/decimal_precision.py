# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _

class DecimalPrecision(models.Model):
    _name = 'decimal.precision'
    _description = 'Decimal Precision'

    name = fields.Char('Usage', index=True, required=True)
    digits = fields.Integer('Digits', required=True, default=2)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', """Only one value can be defined for each given usage!"""),
    ]

    @api.onchange('digits')
    def _onchange_digits(self):
        new_rounding = 1.0 / 10.0**self.digits
        dangerous_uom = self.env['uom.uom'].search([('rounding', '<', new_rounding)])
        if dangerous_uom:
            errors = ["'%s' (id=%s, precision=%s)." % (uom.name, str(uom.id), str(uom.rounding)) for uom in dangerous_uom]
            warning = {
                'title': _('Warning!'),
                'message':
                    _(
                        "You are setting a Decimal Accuracy less precise than"
                        " the UOM:\n %s \n"
                        "This may cause inconsistencies in reservations.\n"
                        "Please increase the rounding of this unit of measure and the global decimal precision."
                     ) % ('\n'.join(errors))
                    ,
            }
            return {'warning': warning}

    @api.model
    @tools.ormcache('application')
    def precision_get(self, application):
        self.env.cr.execute('select digits from decimal_precision where name=%s', (application,))
        res = self.env.cr.fetchone()
        return res[0] if res else 2

    @api.model_cr
    def clear_cache(self):
        """ Deprecated, use `clear_caches` instead. """
        self.clear_caches()

    @api.model_create_multi
    def create(self, vals_list):
        res = super(DecimalPrecision, self).create(vals_list)
        self.clear_caches()
        return res

    @api.multi
    def write(self, data):
        res = super(DecimalPrecision, self).write(data)
        self.clear_caches()
        return res

    @api.multi
    def unlink(self):
        res = super(DecimalPrecision, self).unlink()
        self.clear_caches()
        return res


class DecimalPrecisionFloat(models.AbstractModel):
    """ Override qweb.field.float to add a `decimal_precision` domain option
    and use that instead of the column's own value if it is specified
    """
    _inherit = 'ir.qweb.field.float'


    @api.model
    def precision(self, field, options=None):
        dp = options and options.get('decimal_precision')
        if dp:
            return self.env['decimal.precision'].precision_get(dp)

        return super(DecimalPrecisionFloat, self).precision(field, options=options)

class DecimalPrecisionTestModel(models.Model):
    _name = 'decimal.precision.test'
    _description = 'Decimal Precision Test'

    float = fields.Float()
    float_2 = fields.Float(digits=(16, 2))
    float_4 = fields.Float(digits=(16, 4))
