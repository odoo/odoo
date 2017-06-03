# -*- coding: utf-8 -*-

from openerp import api
from openerp.osv import osv
from openerp.tools.safe_eval import safe_eval as eval
from openerp.addons.website.models.website import slug


class MailGroup(osv.Model):
    _inherit = 'mail.channel'

    @api.cr_uid_ids_context
    def message_get_email_values(self, cr, uid, id, notif_mail=None, context=None):
        res = super(MailGroup, self).message_get_email_values(cr, uid, id, notif_mail=notif_mail, context=context)
        group = self.browse(cr, uid, id, context=context)
        base_url = self.pool['ir.config_parameter'].get_param(cr, uid, 'web.base.url')
        headers = {}
        if res.get('headers'):
            try:
                headers = eval(res['headers'])
            except Exception:
                pass
        headers.update({
            'List-Archive': '<%s/groups/%s>' % (base_url, slug(group)),
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
