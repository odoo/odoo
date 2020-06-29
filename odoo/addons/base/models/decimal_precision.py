# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools
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

    name = fields.Char('Usage', index=True, required=True)
    digits = fields.Integer('Digits', required=True, default=2)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', """Only one value can be defined for each given usage!"""),
    ]

    @api.model
    @tools.ormcache('application')
    def precision_get(self, application):
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

# compatibility for decimal_precision.get_precision(): expose the module in addons namespace
dp = sys.modules['odoo.addons.base.models.decimal_precision']
odoo.addons.decimal_precision = dp
sys.modules['odoo.addons.decimal_precision'] = dp
sys.modules['openerp.addons.decimal_precision'] = dp
