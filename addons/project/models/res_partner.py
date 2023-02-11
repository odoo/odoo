# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools import email_normalize


class ResPartner(models.Model):
    """ Inherits partner and adds Tasks information in the partner form """
    _inherit = 'res.partner'

    task_ids = fields.One2many('project.task', 'partner_id', string='Tasks')
    task_count = fields.Integer(compute='_compute_task_count', string='# Tasks')

    def _compute_task_count(self):
        # retrieve all children partners and prefetch 'parent_id' on them
        all_partners = self.with_context(active_test=False).search([('id', 'child_of', self.ids)])
        all_partners.read(['parent_id'])

        task_data = self.env['project.task'].read_group(
            domain=[('partner_id', 'in', all_partners.ids)],
            fields=['partner_id'], groupby=['partner_id']
        )

        self.task_count = 0
        for group in task_data:
            partner = self.browse(group['partner_id'][0])
            while partner:
                if partner in self:
                    partner.task_count += group['partner_id_count']
                partner = partner.parent_id

# Deprecated: remove me in MASTER
    def _create_portal_users(self):
        partners_without_user = self.filtered(lambda partner: not partner.user_ids)
        if not partners_without_user:
            return self.env['res.users']
        created_users = self.env['res.users']
        for partner in partners_without_user:
            created_users += self.env['res.users'].with_context(no_reset_password=True).sudo()._create_user_from_template({
                'email': email_normalize(partner.email),
                'login': email_normalize(partner.email),
                'partner_id': partner.id,
                'company_id': self.env.company.id,
                'company_ids': [(6, 0, self.env.company.ids)],
                'active': True,
            })
        return created_users
