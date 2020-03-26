# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class CrmTeamMember(models.Model):
    _name = 'crm.team.member'
    _inherit = ['mail.thread']
    _description = 'Sales Team Member'
    _rec_name = 'user_id'

    crm_team_id = fields.Many2one('crm.team', string='Sales Team', required=True)
    user_id = fields.Many2one('res.users', string='Saleman', required=True)  # check responsible field
    name = fields.Char(string="Name", related='user_id.partner_id.display_name', readonly=False)
    active = fields.Boolean(string='Running', default=True)
