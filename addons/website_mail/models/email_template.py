# -*- coding: utf-8 -*-

from openerp.osv import osv
from openerp.tools.translate import _


class EmailTemplate(osv.Model):
    _inherit = 'email.template'

    def action_edit_html(self, cr, uid, ids, context=None):
        if not len(ids) == 1:
            raise ValueError('One and only one ID allowed for this action')
        url = '/website_mail/email_designer?model=email.template&res_id=%d&enable_editor=1' % (ids[0],)
        return {
            'name': _('Edit Template'),
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'self',
        }
