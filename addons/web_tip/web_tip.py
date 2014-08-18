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

from openerp.osv import osv, fields


class tip(osv.Model):
    _name = 'web.tip'
    _description = 'Tips'

    def _is_consumed(self, cr, uid, ids, fields, arg, context=None):
        results = {}
        records = self.read(cr, uid, ids, ['user_ids'])
        for rec in records:
            if uid in rec['user_ids']:
                results[rec['id']] = True
            else:
                results[rec['id']] = False
        return results

    _columns = {
        'title': fields.char('Tip title'),
        'description': fields.html('Tip Description', required=True),
        'action_id': fields.many2one('ir.actions.act_window', string="Action",
            help="The action that will trigger the tip"),
        'model': fields.char("Model", help="Model name on which to trigger the tip, e.g. 'res.partner'."),
        'type': fields.char("Type", help="Model type, e.g. lead or opportunity for crm.lead"),
        'mode': fields.char("Mode", help="Mode, e.g. kanban, form"),
        'trigger_selector': fields.char('Trigger selector', help='CSS selectors used to trigger the tip, separated by a comma (ANDed).'),
        'highlight_selector': fields.char('Highlight selector', help='CSS selector for the element to highlight'),
        'end_selector': fields.char('End selector', help='CSS selector used to end the tip'),
        'end_event': fields.char('End event', help='Event to end the tip'),
        'placement': fields.char('Placement', help='Popover placement, bottom, top, left or right'),
        'user_ids': fields.many2many('res.users', string='Consumed by'),
        'is_consumed': fields.function(_is_consumed, type='boolean', string='Tip consumed')
    }

    _defaults = {
        'placement': 'auto',
        'end_event': 'click'
    }

    def consume(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {
            'user_ids': [(4, uid)]
        }, context=context)
