# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from openerp.osv import fields, osv

class goal_manual_wizard(osv.TransientModel):
    """Wizard to update a manual goal"""
    _name = 'gamification.goal.wizard'
    _columns = {
        'goal_id': fields.many2one("gamification.goal", string='Goal', required=True),
        'current': fields.float('Current'),
    }

    def action_update_current(self, cr, uid, ids, context=None):
        """Wizard action for updating the current value"""

        goal_obj = self.pool.get('gamification.goal')

        for wiz in self.browse(cr, uid, ids, context=context):
            towrite = {
                'current': wiz.current,
                'goal_id': wiz.goal_id.id,
                'to_update': False,
            }
            goal_obj.write(cr, uid, [wiz.goal_id.id], towrite, context=context)
            goal_obj.update(cr, uid, [wiz.goal_id.id], context=context)
        return {}
