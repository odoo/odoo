# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)


class DecimalPrecision(models.Model):
    _name = 'decimal.precision'
    _description = 'Decimal Precision'

    name = fields.Char('Usage', required=True)
    min_digits = fields.Integer(
        "Minimum Digits to Display",
        required=True,
        compute="_compute_min_digits",
        readonly=False,
        store=True,
    )
    max_digits = fields.Integer('Maximum Digits to Store', required=True, default=2)

    _name_uniq = models.Constraint(
        'unique (name)',
        "Only one value can be defined for each given usage!",
    )

    @api.depends('max_digits')
    def _compute_min_digits(self):
        for dec_precision in self:
            if not dec_precision.min_digits or dec_precision.min_digits > dec_precision.max_digits:
                dec_precision.min_digits = dec_precision.max_digits

    @api.constrains('min_digits')
    def _check_min_digits_not_greater_than_max_digits(self):
        for dec_precision in self:
            if dec_precision.min_digits > dec_precision.max_digits:
                raise ValidationError(self.env._("Minimum Digits cannot be greater than Maximum Digits."))

    @api.model
    @tools.ormcache('application')
    def precision_get(self, application):
        self.flush_model(['name', 'max_digits'])
        self.env.cr.execute('select max_digits from decimal_precision where name=%s', (application,))
        res = self.env.cr.fetchone()
        return res[0] if res else 2

    def _get_min_digits(self, application):
        self.flush_model(['name', 'min_digits', 'max_digits'])
        self.env.cr.execute('select min_digits from decimal_precision where name=%s', (application,))
        res = self.env.cr.fetchone()
        return res[0] if res else 2

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        self.env.registry.clear_cache()
        return res

    def write(self, vals):
        res = super().write(vals)
        self.env.registry.clear_cache()
        return res

    def unlink(self):
        res = super().unlink()
        self.env.registry.clear_cache()
        return res

    @api.onchange('digits')
    def _onchange_digits_warning(self):
        if self.max_digits < self._origin.max_digits:
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
