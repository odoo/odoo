# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api
import json
from odoo.tools import float_repr


class AnalyticMixin(models.AbstractModel):
    _name = 'analytic.mixin'
    _description = 'Analytic Mixin'

    # We create 2 different fields, with a computed binary field, so we don't have to decode encode each time the json.
    # We also format the float values of the stored field, so we can use it as key (for tax detail for ex.)
    analytic_distribution_stored_char = fields.Char(
        compute="_compute_analytic_distribution_stored_char", store=True, copy=True)
    analytic_distribution = fields.Binary(
        string="Analytic",
        compute="_compute_analytic_distribution",
        inverse="_inverse_analytic_distribution",
        readonly=False,
    )

    def _compute_analytic_distribution_stored_char(self):
        pass

    @api.depends('analytic_distribution_stored_char')
    def _compute_analytic_distribution(self):
        for record in self:
            if record.analytic_distribution_stored_char:
                distribution_to_return = {}
                distribution_json = json.loads(record.analytic_distribution_stored_char)
                for account, distribution in distribution_json.items():
                    distribution_to_return[int(account)] = float(distribution)
                # Check if the account exists, can be removed when we have a constraint between account and model
                account_ids = self.env['account.analytic.account'].browse(distribution_to_return.keys()).exists().ids
                record.analytic_distribution = {account_id: distribution_to_return[account_id] for account_id in account_ids}

    @api.onchange('analytic_distribution')
    def _inverse_analytic_distribution(self):
        decimal_precision = self.env['decimal.precision'].precision_get('Percentage Analytic')
        self.env.remove_to_compute(self._fields['analytic_distribution_stored_char'], self)
        for record in self:
            if not record.analytic_distribution:
                record.analytic_distribution_stored_char = None
            else:
                distribution_to_return = {}
                for account, distribution in record.analytic_distribution.items():
                    distribution_to_return[account] = float_repr(distribution, decimal_precision)
                record.analytic_distribution_stored_char = json.dumps(distribution_to_return)
