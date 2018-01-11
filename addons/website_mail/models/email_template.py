# -*- coding: utf-8 -*-

from openerp.osv import osv
from openerp.tools.translate import _


class EmailTemplate(osv.Model):
    _inherit = 'email.template'

    def action_edit_html(self, cr, uid, ids, context=None):
        if not len(ids) == 1:
            raise ValueError('One and only one ID allowed for this action')
        if not context.get('params'):
            action_id = self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'mass_mailing.action_email_template_marketing')
        else:
            action_id = context['params']['action']

        url = '/website_mail/email_designer?model=email.template&res_id=%d&return_action=%d&enable_editor=1' % (ids[0], action_id)
        return {
            'name': _('Edit Template'),
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'self',
        }
