# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


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
