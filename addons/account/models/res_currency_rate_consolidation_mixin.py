# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class ConsolidationRateMixin(models.AbstractModel):
    _name = 'res.currency.rate.consolidation.mixin'
    _description = "Enable multi company consolidation"

    consolidation_rate = fields.Float(
        string="Rate",
        compute='_compute_consolidation_rate',
        compute_sudo=True,
        digits=0,
        aggregator=None,
    )
    consolidation_currency_id = fields.Many2one(
        comodel_name='res.currency',
        compute='_compute_consolidation_currency_id',
        compute_sudo=True,
    )

    @api.depends_context('allowed_company_ids')
    def _compute_consolidation_rate(self):
        if len(self.env.companies.currency_id) <= 1:
            self.consolidation_rate = 1
            return
        query = self._search([('id', 'in', self.ids)])
        line2rate = dict(self.env.execute_query(query.select(query.table.id, query.table.consolidation_rate)))
        for record in self:
            record.consolidation_rate = line2rate.get(record._origin.id, 1)

    @api.depends_context('company')
    def _compute_consolidation_currency_id(self):
        self.consolidation_currency_id = self.env.company.currency_id
