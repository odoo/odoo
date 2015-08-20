# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools.safe_eval import safe_eval as eval
from odoo.addons.website.models.website import slug


class MailGroup(models.Model):
    _inherit = 'mail.channel'

    @api.multi
    def message_get_email_values(self, notif_mail=None):
        self.ensure_one()
        res = super(MailGroup, self).message_get_email_values(notif_mail=notif_mail)
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        headers = {}
        if res.get('headers'):
            try:
                headers = eval(res['headers'])
            except Exception:
                pass
        headers.update({
            'List-Archive': '<%s/groups/%s>' % (base_url, slug(self)),
            'List-Subscribe': '<%s/groups>' % (base_url),
            'List-Unsubscribe': '<%s/groups?unsubscribe>' % (base_url,),
        })
        res['headers'] = repr(headers)
        return res
