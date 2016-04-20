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

    @api.multi
    def _send_confirmation_email(self, partner_ids, unsubscribe=False):
        if unsubscribe:
            template = self.env.ref('website_mail_channel.mail_template_list_unsubscribe')
            route = "/groups/unsubscribe/%s"
        else:
            template = self.env.ref('website_mail_channel.mail_template_list_unsubscribe')
            route = "/groups/subscribe/%s"

        for partner_id in partner_ids:
            # generate a new token per subscriber
            token = self.env['ir.token'].sudo().create({
                'res_model': 'mail.channel',
                'res_id': self.id,
                'partner_id': partner_id,
            })

            template.with_context(
                token=token,
                token_url=token._generate_token_url(route)
            ).send_mail(self.id,
                        force_send=True,
                        email_values={'recipient_ids': [(4, partner_id)]}
            )

        return True
