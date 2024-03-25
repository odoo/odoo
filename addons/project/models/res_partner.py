# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError
from odoo.tools import email_normalize
from odoo.osv import expression


class ResPartner(models.Model):
    """ Inherits partner and adds Tasks information in the partner form """
    _inherit = 'res.partner'

    project_ids = fields.One2many('project.project', 'partner_id', string='Projects')
    task_ids = fields.One2many('project.task', 'partner_id', string='Tasks')
    task_count = fields.Integer(compute='_compute_task_count', string='# Tasks')

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

    @api.model
    def get_mention_suggestions_from_task(self, task_id, search, limit=8):
        """Return 'limit'-first partners' such that the name or email matches a 'search' string.
        Prioritize partners that are also (internal) users, and then extend the research to all partners.
        Only followers of the given task or followers of its project are returned.
        The return format is a list of partner data (as per returned by `mail_partner_format()`).
        """
        task_sudo = self.env['project.task'].sudo().search([('id', '=', task_id)])
        shared_project_sudo = task_sudo.project_id
        shared_project = shared_project_sudo.with_user(self.env.user)
        if not (shared_project and shared_project._check_project_sharing_access()):
            return []
        try:
            shared_project.check_access_rights('read')
            shared_project.check_access_rule('read')
        except AccessError:
            return []
        followers = shared_project_sudo.message_follower_ids + task_sudo.message_follower_ids
        domain = expression.AND(
            [
                self._get_mention_suggestions_domain(search),
                [("id", "in", followers.partner_id.ids)],
            ]
        )
        partners = self.sudo()._search_mention_suggestions(domain, limit)
        return list(partners.mail_partner_format().values())
