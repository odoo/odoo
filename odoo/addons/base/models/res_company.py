# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Company(models.Model):
    _name = "res.company"
    _description = 'Companies'
    _order = 'name'

    def copy(self, default=None):
        raise UserError(_('Duplicating a company is not allowed. Please create a new company instead.'))

    name = fields.Char(related='partner_id.name', string='Company Name', required=True, store=True, readonly=False)
    partner_id = fields.Many2one('res.partner', string='Partner', required=True)
    user_ids = fields.Many2many('res.users', 'res_company_users_rel', 'cid', 'user_id', string='Accepted Users')
    email = fields.Char(related='partner_id.email', store=True, readonly=False)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The company name must be unique !')
    ]

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        context = dict(self.env.context)
        newself = self
        if context.pop('user_preference', None):
            # We browse as superuser. Otherwise, the user would be able to
            # select only the currently visible companies (according to rules,
            # which are probably to allow to see the child companies) even if
            # she belongs to some other companies.
            companies = self.env.user.company_ids
            args = (args or []) + [('id', 'in', companies.ids)]
            newself = newself.sudo()
        return super(Company, newself.with_context(context))._name_search(name=name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)

    # deprecated, use clear_caches() instead
    def cache_restart(self):
        self.clear_caches()

    def _get_create_partner_values(self, vals):
        return {
            'name': vals['name'],
            'email': vals.get('email'),
        }

    @api.model
    def create(self, vals):
        if not vals.get('name') or vals.get('partner_id'):
            self.clear_caches()
            return super().create(vals)
        partner = self.env['res.partner'].create(self._get_create_partner_values(vals))
        # compute stored fields, for example address dependent fields
        partner.flush()
        vals['partner_id'] = partner.id
        self.clear_caches()
        company = super().create(vals)
        # The write is made on the user to set it automatically in the multi company group.
        self.env.user.write({'company_ids': [(4, company.id)]})
        return company

    def write(self, values):
        self.clear_caches()
        res = super(Company, self).write(values)
        return res
