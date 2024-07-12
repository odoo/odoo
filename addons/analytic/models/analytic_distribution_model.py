# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import SQL
from odoo.exceptions import UserError


class AccountAnalyticDistributionModel(models.Model):
    _name = 'account.analytic.distribution.model'
    _inherit = 'analytic.mixin'
    _description = 'Analytic Distribution Model'
    _rec_name = 'create_date'
    _order = 'sequence, id desc'

    sequence = fields.Integer(default=10)
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        ondelete='cascade',
        help="Select a partner for which the analytic distribution will be used (e.g. create new customer invoice or Sales order if we select this partner, it will automatically take this as an analytic account)",
    )
    partner_category_id = fields.Many2one(
        'res.partner.category',
        string='Partner Category',
        ondelete='cascade',
        help="Select a partner category for which the analytic distribution will be used (e.g. create new customer invoice or Sales order if we select this partner, it will automatically take this as an analytic account)",
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        ondelete='cascade',
        help="Select a company for which the analytic distribution will be used (e.g. create new customer invoice or Sales order if we select this company, it will automatically take this as an analytic account)",
    )

    @api.constrains('company_id')
    def _check_company_accounts(self):
        """Ensure accounts specific to a company isn't used in any distribution model that wouldn't be specific to the company"""
        query = SQL(
            """
            SELECT model.id
              FROM account_analytic_distribution_model model
              JOIN account_analytic_account account
                ON ARRAY[account.id::text] && %s
             WHERE account.company_id IS NOT NULL AND model.id = ANY(%s)
               AND (model.company_id IS NULL 
                OR model.company_id != account.company_id)
            """,
            self._query_analytic_accounts('model'),
            self.ids,
        )
        self.flush_model(['company_id', 'analytic_distribution'])
        self.env.cr.execute(query)
        if self.env.cr.dictfetchone():
            raise UserError(_('You defined a distribution with analytic account(s) belonging to a specific company but a model shared between companies or with a different company'))

    @api.model
    def _get_distribution(self, vals):
        """ Returns the combined distribution from all matching models based on the vals dict provided
            This method should be called to prefill analytic distribution field on several models """
        applicable_models = self._get_applicable_models(vals)

        res = {}
        applied_plans = self.env['account.analytic.plan']
        for model in applicable_models:
            # ignore model if it contains an account having a root plan that was already applied
            if not applied_plans & model.distribution_analytic_account_ids.root_plan_id:
                res |= model.analytic_distribution
                applied_plans += model.distribution_analytic_account_ids.root_plan_id
        return res

    @api.model
    def _get_default_search_domain_vals(self):
        return {
            'company_id': False,
            'partner_id': False,
            'partner_category_id': [],
        }

    @api.model
    def _get_applicable_models(self, vals):
        vals = self._get_default_search_domain_vals() | vals
        domain = []
        for fname, value in vals.items():
            domain += self._create_domain(fname, value)
        return self.search(domain)

    def _create_domain(self, fname, value):
        if fname == 'partner_category_id':
            value += [False]
            return [(fname, 'in', value)]
        else:
            return [(fname, 'in', [value, False])]

    def action_read_distribution_model(self):
        self.ensure_one()
        return {
            'name': self.display_name,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.analytic.distribution.model',
            'res_id': self.id,
        }
