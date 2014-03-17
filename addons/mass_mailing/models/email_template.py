# -*- coding: utf-8 -*-

from openerp.tools.translate import _
from openerp.osv import osv, fields


class EmailTemplate(osv.Model):
    """Add the mass mailing campaign data to mail"""
    _name = 'email.template'
    _inherit = ['email.template']

    _columns = {
        'use_in_mass_mailing': fields.boolean('Available for mass mailing campaigns'),
    }

    def action_new_mailing(self, cr, uid, ids, context=None):
        ctx = dict(context)
        ctx.update({
            'default_template_id': ids[0],
        })
        return {
            'name': _('Create a Mass Mailing'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.mass_mailing',
            'views': [(False, 'form')],
            'view_id': False,
            # 'target': 'new',
            'context': ctx,
        }
