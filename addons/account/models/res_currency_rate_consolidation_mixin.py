# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

from odoo import api, fields, models
from odoo.tools import SQL


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
        consolidation_rate = self._consolidation_rate_sql(query.table)
        line2rate = dict(self.env.execute_query(query.select(query.table.id, consolidation_rate)))
        for record in self:
            record.consolidation_rate = line2rate.get(record._origin.id, 1)

    def _consolidation_rate_sql(self, table):
        if len(self.env.companies.currency_id) == 1:
            return SQL("1")

        date_to = fields.Date.to_date(self.env.context['date_to'])
        _historical, _average, current = self.env['res.currency']._get_parsed_rates(self.env.companies - self.env.company, date_to, date_to)

        raw_rates_alias = table._make_alias('raw_currencies')
        raw_rates_table = SQL("(SELECT %(current)s::jsonb AS current)", current=json.dumps(current))
        cta_alias = table._make_alias('current')
        conversion_table = SQL(
            "(SELECT (%(current)s->>(%(base_line_company)s::text))::numeric AS rate)",
            base_line_company=table.company_id,
            current=raw_rates_alias.current,
        )
        table._query.add_join(kind='JOIN', alias=raw_rates_alias, table=raw_rates_table, condition=SQL("TRUE"))
        table._query.add_join(kind='LEFT JOIN LATERAL', alias=cta_alias, table=conversion_table, condition=SQL("TRUE"))
        return SQL("COALESCE(%s, 1)", cta_alias.rate)

    @api.depends_context('company')
    def _compute_consolidation_currency_id(self):
        self.consolidation_currency_id = self.env.company.currency_id
