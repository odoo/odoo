# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class CrmTeam(models.Model):
    _name = "crm.team"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = "Sales Team"
    _order = "name"

    @api.model
    @api.returns('self', lambda value: value.id)
    def _get_default_team_id(self, user_id=None):
        team_id = self.env['crm.team'].browse(self.env.context.get('default_team_id'))
        if not team_id:
            if user_id is None:
                user_id = self.env.uid
            team_id = self.env['crm.team'].search([
                '|',
                ('user_id', '=', user_id),
                ('member_ids', 'in', [user_id])],
                limit=1) or self.env.ref('sales_team.team_sales_department')
        return team_id

    name = fields.Char('Sales Team', required=True, translate=True)
    code = fields.Char()
    active = fields.Boolean(default=True, help="If the active field is set to false, it will allow you to hide the sales team without removing it.")
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env['res.company']._company_default_get('crm.team'))
    user_id = fields.Many2one('res.users', string='Team Leader')
    member_ids = fields.One2many('res.users', 'sale_team_id', string='Team Members')
    reply_to = fields.Char(string='Reply-To',
                           help="The email address put in the 'Reply-To' of all emails sent by Odoo about cases in this sales team")
    color = fields.Integer(string='Color Index', help="The color of the team")

    _sql_constraints = [
        ('code_uniq', 'unique (code)', 'The code of the sales team must be unique !')
    ]

    @api.model
    def create(self, values):
        return super(CrmTeam, self.with_context(mail_create_nosubscribe=True)).create(values)
