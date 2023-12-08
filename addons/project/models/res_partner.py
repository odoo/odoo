# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import email_normalize


class ResPartner(models.Model):
    """ Inherits partner and adds Tasks information in the partner form """
    _inherit = 'res.partner'

    project_ids = fields.One2many('project.project', 'partner_id', string='Projects', export_string_translation=False)
    task_ids = fields.One2many('project.task', 'partner_id', string='Tasks', export_string_translation=False)
    task_count = fields.Integer(compute='_compute_task_count', string='# Tasks', export_string_translation=False)

    @api.constrains('company_id', 'project_ids')
    def _ensure_same_company_than_projects(self):
        for partner in self:
            if partner.company_id and partner.project_ids.company_id and partner.project_ids.company_id != partner.company_id:
                raise UserError(_("Partner company cannot be different from its assigned projects' company"))

    @api.constrains('company_id', 'task_ids')
    def _ensure_same_company_than_tasks(self):
        for partner in self:
            if partner.company_id and partner.task_ids.company_id and partner.task_ids.company_id != partner.company_id:
                raise UserError(_("Partner company cannot be different from its assigned tasks' company"))

    def _compute_task_count(self):
        # retrieve all children partners and prefetch 'parent_id' on them
        all_partners = self.with_context(active_test=False).search_fetch(
            [('id', 'child_of', self.ids)],
            ['parent_id'],
        )
        task_data = self.env['project.task']._read_group(
            domain=[('partner_id', 'in', all_partners.ids)],
            groupby=['partner_id'], aggregates=['__count']
        )
        self_ids = set(self._ids)

        self.task_count = 0
        for partner, count in task_data:
            while partner:
                if partner.id in self_ids:
                    partner.task_count += count
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

    def action_view_tasks(self):
        self.ensure_one()
        action = {
            **self.env["ir.actions.actions"]._for_xml_id("project.project_task_action_from_partner"),
            'display_name': _("%(partner_name)s's Tasks", partner_name=self.name),
            'context': {
                'default_partner_id': self.id,
            },
        }
        all_child = self.with_context(active_test=False).search([('id', 'child_of', self.ids)])
        search_domain = [('partner_id', 'in', (self | all_child).ids)]
        if self.task_count <= 1:
            task_id = self.env['project.task'].search(search_domain, limit=1)
            action['res_id'] = task_id.id
            action['views'] = [(view_id, view_type) for view_id, view_type in action['views'] if view_type == "form"]
        else:
            action['domain'] = search_domain
        return action
