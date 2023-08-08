# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
import odoo.addons

import logging
import sys
_logger = logging.getLogger(__name__)


def get_precision(application):
    _logger.warning("Deprecated call to decimal_precision.get_precision(<application>), use digits=<application> instead")
    return application


class DecimalPrecision(models.Model):
    _name = 'decimal.precision'
    _description = 'Decimal Precision'

    name = fields.Char('Usage', required=True)
    digits = fields.Integer('Digits', required=True, default=2)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', """Only one value can be defined for each given usage!"""),
    ]

    @api.model
    @tools.ormcache('application')
    def precision_get(self, application):
        self.flush_model(['name', 'digits'])
        self.env.cr.execute('select digits from decimal_precision where name=%s', (application,))
        res = self.env.cr.fetchone()
        return res[0] if res else 2

    @api.model_create_multi
    def create(self, vals_list):
        res = super(DecimalPrecision, self).create(vals_list)
        self.clear_caches()
        return res

    def write(self, data):
        res = super(DecimalPrecision, self).write(data)
        self.clear_caches()
        return res

    def unlink(self):
        res = super(DecimalPrecision, self).unlink()
        self.clear_caches()
        return res

    @api.onchange('digits')
    def _onchange_digits_warning(self):
        if self.digits < self._origin.digits:
            return {
                'warning': {
                    'title': _("Warning for %s", self.name),
                    'message': _(
                        "The precision has been reduced for %s.\n"
                        "Note that existing data WON'T be updated by this change.\n\n"
                        "As decimal precisions impact the whole system, this may cause critical issues.\n"
                        "E.g. reducing the precision could disturb your financial balance.\n\n"
                        "Therefore, changing decimal precisions in a running database is not recommended.",
                        self.name,
                    )
                }
            }

# compatibility for decimal_precision.get_precision(): expose the module in addons namespace
dp = sys.modules['odoo.addons.base.models.decimal_precision']
odoo.addons.decimal_precision = dp
sys.modules['odoo.addons.decimal_precision'] = dp
sys.modules['openerp.addons.decimal_precision'] = dp
