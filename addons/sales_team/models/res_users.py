# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    crm_team_ids = fields.Many2many(
        'crm.team', 'crm_team_member', 'user_id', 'crm_team_id', string='Sales Teams',
        check_company=True, copy=False, readonly=True,
        compute='_compute_crm_team_ids', search='_search_crm_team_ids')
    crm_team_member_ids = fields.One2many('crm.team.member', 'user_id', string='Sales Team Members')
    sale_team_id = fields.Many2one(
        'crm.team', string='User Sales Team', compute='_compute_sale_team_id',
        readonly=True, store=True,
        help="Main user sales team. Used notably for pipeline, or to set sales team in invoicing or subscription.")

    @api.depends('crm_team_member_ids.active')
    def _compute_crm_team_ids(self):
        for user in self:
            user.crm_team_ids = user.crm_team_member_ids.crm_team_id

    def _search_crm_team_ids(self, operator, value):
        # Equivalent to `[('crm_team_member_ids.crm_team_id', operator, value)]`,
        # but we inline the ids directly to simplify final queries and improve performance,
        # as it's part of a few ir.rules.
        # If we're going to inject too many `ids`, we fall back on the default behavior
        # to avoid a performance regression.
        IN_MAX = 10_000
        domain = [('crm_team_member_ids.crm_team_id', operator, value)]
        user_ids = self.env['res.users'].with_context(active_test=False)._search(domain, limit=IN_MAX).get_result_ids()
        if len(user_ids) < IN_MAX:
            return [('id', 'in', user_ids)]

        return domain

    @api.depends('crm_team_member_ids.crm_team_id', 'crm_team_member_ids.create_date', 'crm_team_member_ids.active')
    def _compute_sale_team_id(self):
        for user in self:
            if not user.crm_team_member_ids.ids:
                user.sale_team_id = False
            else:
                sorted_memberships = user.crm_team_member_ids  # sorted by create date
                user.sale_team_id = sorted_memberships[0].crm_team_id if sorted_memberships else False

    def action_archive(self):
        self.env['crm.team.member'].search([('user_id', 'in', self.ids)]).action_archive()
        return super().action_archive()
