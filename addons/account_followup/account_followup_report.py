# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2004-2015 OpenErp S.A. (<http://odoo.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api, tools
import time


class account_report_context_followup(models.TransientModel):
    _inherit = "account.report.context.followup"

    level = fields.Many2one('account_followup.followup.line')
    summary = fields.Char(default=lambda s: s.level and s.level.description.replace('\n', '<br />') or s.env['res.company'].default_get(['overdue_msg'])['overdue_msg'])

    @api.multi
    def do_manual_action(self):
        for context in self:
            msg = 'Manual action done :\n' + context.level.manual_action_note
            context.partner_id.message_post(body=msg, subtype='account.followup_logged_action')

    def create(self, vals):
        if 'level' in vals:
            summary = self.env['account_followup.followup.line'].browse(vals['level']).description.replace('\n', '<br />')
            vals.update({
                'summary': summary % {
                    'partner_name': self.env['res.partner'].browse(vals['partner_id']).name,
                    'date': time.strftime('%Y-%m-%d'),
                    'user_signature': self.env.user.signature or '',
                    'company_name': self.env['res.partner'].browse(vals['partner_id']).parent_id.name,
                }
            })
        return super(account_report_context_followup, self).create(vals)
