# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
