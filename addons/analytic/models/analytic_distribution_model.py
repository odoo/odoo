# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class NonMatchingDistribution(Exception):
    pass


class AccountAnalyticDistributionModel(models.Model):
    _name = 'account.analytic.distribution.model'
    _inherit = 'analytic.mixin'
    _description = 'Analytic Distribution Model'
    _rec_name = 'create_date'
    _order = 'id desc'

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
        query = """
            SELECT model.id
              FROM account_analytic_distribution_model model
              JOIN account_analytic_account account
                ON model.analytic_distribution ? CAST(account.id AS VARCHAR)
             WHERE account.company_id IS NOT NULL 
               AND (model.company_id IS NULL 
                OR model.company_id != account.company_id)
        """
        self.flush_model(['company_id', 'analytic_distribution'])
        self.env.cr.execute(query)
        if self.env.cr.dictfetchone():
            raise UserError(_('You defined a distribution with analytic account(s) belonging to a specific company but a model shared between companies or with a different company'))

    @api.model
    def _get_distribution(self, vals):
        """ Returns the distribution model that has the most fields that corresponds to the vals given
            This method should be called to prefill analytic distribution field on several models """
        domain = []
        for fname, value in vals.items():
            domain += self._create_domain(fname, value) or []
        best_score = 0
        res = {}
        fnames = set(self._get_fields_to_check())
        for rec in self.search(domain):
            try:
                score = sum(rec._check_score(key, vals.get(key)) for key in fnames)
                if score > best_score:
                    res = rec.analytic_distribution
                    best_score = score
            except NonMatchingDistribution:
                continue
        return res

    def _get_fields_to_check(self):
        return (
            {field.name for field in self._fields.values() if not field.manual}
            - set(self.env['analytic.mixin']._fields)
            - set(models.MAGIC_COLUMNS) - {'display_name', '__last_update'}
        )

    def _check_score(self, key, value):
        self.ensure_one()
        if key == 'company_id':
            if not self.company_id or value == self.company_id.id:
                return 1 if self.company_id else 0.5
            raise NonMatchingDistribution
        if not self[key]:
            return 0
        if value and ((self[key].id in value) if isinstance(value, (list, tuple))
                      else (value.startswith(self[key])) if key.endswith('_prefix')
                      else (value == self[key].id)
                      ):
            return 1
        raise NonMatchingDistribution

    def _create_domain(self, fname, value):
        if not value:
            return False
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
