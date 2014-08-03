# -*- coding: utf-8 -*-

from openerp.osv import osv
from openerp.tools.safe_eval import safe_eval as eval


class MailGroup(osv.Model):
    _inherit = 'mail.group'

    def message_get_email_values(self, cr, uid, id, notif_mail=None, context=None):
        res = super(MailGroup, self).message_get_email_values(cr, uid, id, notif_mail=notif_mail, context=context)
        group = self.browse(cr, uid, id, context=context)
        base_url = self.pool['ir.config_parameter'].get_param(cr, uid, 'web.base.url')
        try:
            headers = eval(res.get('headers', '{}'))
        except Exception:
            headers = {}
        headers.update({
            'List-Archive': '<%s/groups/%s>' % (base_url, group.id),
            'List-Subscribe': '<%s/groups>' % (base_url),
            'List-Unsubscribe': '<%s/groups>' % (base_url),
        })
        res['headers'] = '%s' % headers
        return res
