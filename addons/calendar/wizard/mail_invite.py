# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv

from odoo.addons.calendar.models.calendar import get_real_ids


class invite_wizard(osv.osv_memory):
    _inherit = 'mail.wizard.invite'

    def default_get(self, cr, uid, fields, context=None):
        '''
        in case someone clicked on 'invite others' wizard in the followers widget, transform virtual ids in real ids
        '''
        if 'default_res_id' in context:
            context = dict(context, default_res_id=get_real_ids(context['default_res_id']))
        result = super(invite_wizard, self).default_get(cr, uid, fields, context=context)
        if 'res_id' in result:
            result['res_id'] = get_real_ids(result['res_id'])
        return result
