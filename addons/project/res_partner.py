# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields,osv

class res_partner(osv.osv):
    def _task_count(self, cr, uid, ids, field_name, arg, context=None):
        task_data = self.pool['project.task'].read_group(cr, uid, [('partner_id', 'in', ids)], ['partner_id'], ['partner_id'], context=context)
        task_dict = { data['partner_id'][0]: data['partner_id_count'] for data in task_data }
        return { partner_id: task_dict.get(partner_id) for partner_id in ids }
    
    """ Inherits partner and adds Tasks information in the partner form """
    _inherit = 'res.partner'
    _columns = {
        'task_ids': fields.one2many('project.task', 'partner_id', 'Tasks'),
        'task_count': fields.function(_task_count, string='# Tasks', type='integer'),
    }
