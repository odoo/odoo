##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2009-Today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from openerp import models, fields, api


class tip(models.Model):
    _name = 'web.tip'
    _description = 'Tips'

    @api.one
    @api.depends('user_ids')
    def _is_consumed(self):
        self.is_consumed = self.env.user in self.user_ids

    title = fields.Char('Tip title')
    description = fields.Html('Tip Description', required=True)
    action_id = fields.Many2one('ir.actions.act_window', string="Action",
        help="The action that will trigger the tip")
    model = fields.Char("Model", help="Model name on which to trigger the tip, e.g. 'res.partner'.")
    type = fields.Char("Type", help="Model type, e.g. lead or opportunity for crm.lead")
    mode = fields.Char("Mode", help="Mode, e.g. kanban, form")
    trigger_selector = fields.Char('Trigger selector', help='CSS selectors used to trigger the tip, separated by a comma (ANDed).')
    highlight_selector = fields.Char('Highlight selector', help='CSS selector for the element to highlight')
    end_selector = fields.Char('End selector', help='CSS selector used to end the tip')
    end_event = fields.Char('End event', help='Event to end the tip', default='click')
    placement = fields.Char('Placement', help='Popover placement, bottom, top, left or right', default='auto')
    user_ids = fields.Many2many('res.users', string='Consumed by')
    is_consumed = fields.Boolean(string='Tip consumed', compute='_is_consumed')

    @api.multi
    def consume(self):
       self.write({'user_ids': [(4, self.env.uid)]})
