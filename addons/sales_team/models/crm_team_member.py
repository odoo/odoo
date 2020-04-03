# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class CrmTeamMember(models.Model):
    _name = 'crm.team.member'
    _inherit = ['mail.thread']
    _description = 'Sales Team Member'
    _rec_name = 'user_id'
    _order = 'create_date ASC'

    crm_team_id = fields.Many2one(
        'crm.team', string='Sales Team',
        default=False,  # TDE: temporary fix to activate depending computed fields
        index=True, required=True)
    user_id = fields.Many2one(
        'res.users', string='Salesman',   # check responsible field
        index=True, ondelete='cascade', required=True,
        domain="['&', ('share', '=', False), ('id', 'not in', user_in_teams_ids)]")
    user_in_teams_ids = fields.Many2many(
        'res.users', compute='_compute_user_in_teams_ids',
        help='UX: Give users not to add in the currently chosen team to avoid duplicates')
    active = fields.Boolean(string='Active', default=True)
    # salesman information
    image_1920 = fields.Image("Image", related="user_id.image_1920", max_width=1920, max_height=1920)
    image_128 = fields.Image("Image (128)", related="user_id.image_128", max_width=128, max_height=128)
    name = fields.Char(string='Name', related='user_id.display_name', readonly=False)
    email = fields.Char(string='Email', related='user_id.email')
    phone = fields.Char(string='Phone', related='user_id.phone')
    mobile = fields.Char(string='Mobile', related='user_id.mobile')
    company_id = fields.Many2one('res.company', string='Company', related='user_id.company_id')

    _sql_constraints = [
        ('crm_team_member_unique',
         'UNIQUE(crm_team_id,user_id)',
         'Error, team / user memberships should not be duplicated.'),
    ]

    @api.depends('crm_team_id')
    @api.depends_context('default_crm_team_id')
    def _compute_user_in_teams_ids(self):
        for member in self:
            if member.crm_team_id:
                member.user_in_teams_ids = member.crm_team_id.member_ids
            elif self.env.context.get('default_crm_team_id'):
                member.user_in_teams_ids = self.env['crm.team'].browse(self.env.context['default_crm_team_id']).member_ids
            else:
                member.user_in_teams_ids = self.env['res.users']
