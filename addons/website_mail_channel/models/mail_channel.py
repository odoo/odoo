# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hmac

from werkzeug import urls

from odoo import api, models
from odoo.tools.safe_eval import safe_eval
from odoo.addons.http_routing.models.ir_http import slug


class MailGroup(models.Model):
    _inherit = 'mail.channel'

    @api.multi
    def _notify_specific_email_values(self, message):
        res = super(MailGroup, self)._notify_specific_email_values(message)
        try:
            headers = safe_eval(res.get('headers', dict()))
        except Exception:
            headers = {}
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        headers['List-Archive'] = '<%s/groups/%s>' % (base_url, slug(self)),
        headers['List-Subscribe'] = '<%s/groups>' % (base_url),
        headers['List-Unsubscribe'] = '<%s/groups?unsubscribe>' % (base_url,),
        res['headers'] = repr(headers)
        return res

    @api.multi
    def _send_confirmation_email(self, partner_ids, unsubscribe=False):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        route = "/groups/%(action)s/%(channel)s/%(partner)s/%(token)s"
        if unsubscribe:
            template = self.env.ref('website_mail_channel.mail_template_list_unsubscribe')
            action = 'unsubscribe'
        else:
            template = self.env.ref('website_mail_channel.mail_template_list_subscribe')
            action = 'subscribe'

        for partner_id in partner_ids:
            # generate a new token per subscriber
            token = self._generate_action_token(partner_id, action=action)

            token_url = urls.url_join(base_url, route % {
                'action': action,
                'channel': self.id,
                'partner': partner_id,
                'token': token,
            })
            template.with_context(token_url=token_url).send_mail(self.id,
                force_send=True,
                email_values={'recipient_ids': [(4, partner_id)]}
            )

        return True

    @api.multi
    def _generate_action_token(self, partner_id, action='unsubscribe'):
        self.ensure_one()
        secret = self.env['ir.config_parameter'].sudo().get_param('database.secret')
        data = '$'.join([
                str(self.id),
                str(partner_id),
                action])
        return hmac.new(secret.encode('utf-8'), data.encode('utf-8')).hexdigest()
