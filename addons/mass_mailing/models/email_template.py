# -*- coding: utf-8 -*-

from openerp.tools.translate import _
from openerp.osv import osv, fields


class EmailTemplate(osv.Model):
    """Add the mass mailing campaign data to mail"""
    _name = 'email.template'
    _inherit = ['email.template']
    _columns = {
        'use_in_mass_mailing': fields.boolean('Available for marketing and mailing'),
    }
    def action_new_mailing(self, cr, uid, ids, context=None):
        template = self.browse(cr, uid, ids[0], context=context)
        ctx = dict(context)
        ctx.update({
            'default_mailing_model': template.model,
            'default_template_id': ids[0],
        })
        return {
            'name': _('Create a Mass Mailing'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.mass_mailing',
            'views': [(False, 'form')],
            'context': ctx,
        }


class email_template_preview(osv.TransientModel):
    """ Reinitialize email template preview model to have access to all email.template
    new fields. """
    _name = "email_template.preview"
    _inherit = ['email.template', 'email_template.preview']
