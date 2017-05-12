# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class CrmTeam(models.Model):
    _name = "crm.team"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = "Sales Team"
    _order = "name"

    @api.model
    @api.returns('self', lambda value: value.id if value else False)
    def _get_default_team_id(self, user_id=None):
        if not user_id:
            user_id = self.env.uid
        team_id = None
        if 'default_team_id' in self.env.context:
            team_id = self.env['crm.team'].browse(self.env.context.get('default_team_id'))
        if not team_id or not team_id.exists():
            company_id = self.sudo(user_id).company_id.id
            team_id = self.env['crm.team'].sudo().search([
                '|', ('user_id', '=', user_id), ('member_ids', '=', user_id),
                '|', ('company_id', '=', False), ('company_id', 'child_of', [company_id])
            ], limit=1)
        if not team_id:
            default_team_id = self.env.ref('sales_team.team_sales_department', raise_if_not_found=False)
            if default_team_id and (self.env.context.get('default_type') != 'lead' or default_team_id.use_leads):
                team_id = default_team_id
        return team_id

    name = fields.Char('Sales Team', required=True, translate=True)
    active = fields.Boolean(default=True, help="If the active field is set to false, it will allow you to hide the sales team without removing it.")
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env['res.company']._company_default_get('crm.team'))
    user_id = fields.Many2one('res.users', string='Team Leader')
    member_ids = fields.One2many('res.users', 'sale_team_id', string='Team Members')
    reply_to = fields.Char(string='Reply-To',
                           help="The email address put in the 'Reply-To' of all emails sent by Odoo about cases in this sales team")
    color = fields.Integer(string='Color Index', help="The color of the team")

    @api.model
    def create(self, values):
        return super(CrmTeam, self.with_context(mail_create_nosubscribe=True)).create(values)
