# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools

import logging
_logger = logging.getLogger(__name__)


class DecimalPrecision(models.Model):
    _name = 'decimal.precision'
    _description = 'Decimal Precision'
    _clear_cache_name = 'stable'

    name = fields.Char('Usage', required=True)
    digits = fields.Integer('Digits', required=True, default=2)

    _name_uniq = models.Constraint(
        'unique (name)',
        "Only one value can be defined for each given usage!",
    )

    @api.model
    @tools.ormcache('application', cache='stable')
    def precision_get(self, application):
        self.flush_model(['name', 'digits'])
        self.env.cr.execute('select digits from decimal_precision where name=%s', (application,))
        res = self.env.cr.fetchone()
        return res[0] if res else 2

    @api.onchange('digits')
    def _onchange_digits_warning(self):
        if self.digits < self._origin.digits:
            return {
                'warning': {
                    'title': self.env._("Warning for %s", self.name),
                    'message': self.env._(
                        "The precision has been reduced for %s.\n"
                        "Note that existing data WON'T be updated by this change.\n\n"
                        "As decimal precisions impact the whole system, this may cause critical issues.\n"
                        "E.g. reducing the precision could disturb your financial balance.\n\n"
                        "Therefore, changing decimal precisions in a running database is not recommended.",
                        self.name,
                    )
                }
            }
