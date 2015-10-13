# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models


class CrmTeam(models.Model):
    _name = "crm.team"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = "Sales Team"
    _order = "name"
    _period_number = 5

    @api.model
    def _get_default_team_id(self, user_id=None):
        user_id = user_id or self.env.uid

        team_id = self.env.context.get('default_team_id')
        if not team_id:
            team = self.search(['|', ('user_id', '=', user_id), ('member_ids', 'in', user_id)], limit=1)
            team_id = team.id or self.env['ir.model.data'].xmlid_to_res_id('sales_team.team_sales_department')
        return team_id

    name = fields.Char(string='Sales Team', required=True, translate=True)
    code = fields.Char(size=8)
    active = fields.Boolean(help="If the active field is set to true, it will allow you to hide the sales team without removing it.", default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env['res.company']._company_default_get('crm.team'))
    user_id = fields.Many2one('res.users', string='Team Leader')
    member_ids = fields.One2many('res.users', 'sale_team_id', string='Team Members')
    reply_to = fields.Char(string='Reply-To', help="The email address put in the 'Reply-To' of all emails sent by Odoo about cases in this sales team")
    working_hours = fields.Float(digits=(16, 2))
    color = fields.Integer(string='Color Index')

    _sql_constraints = [
        ('code_uniq', 'unique (code)', 'The code of the sales team must be unique !')
    ]

    @api.model
    def create(self, values):
        return super(CrmTeam, self.with_context(mail_create_nosubscribe=True)).create(values)
