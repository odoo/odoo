# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, tools, _
from odoo.addons.http_routing.models.ir_http import slug


class MailMail(models.Model):
    _inherit = 'mail.mail'

    @api.multi
    def _send_prepare_body(self):
        """ Short-circuit parent method for mail groups, replace the default
            footer with one appropriate for mailing-lists."""
        if self.model == 'mail.channel' and self.res_id:
            # no super() call on purpose, no private links that could be quoted!
            channel = self.env['mail.channel'].browse(self.res_id)
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            vals = {
                'maillist': _('Mailing List'),
                'post_to': _('Post to'),
                'unsub': _('Unsubscribe'),
                'mailto': '%s@%s' % (channel.alias_name, channel.alias_domain),
                'group_url': '%s/groups/%s' % (base_url, slug(channel)),
                'unsub_url': '%s/groups?unsubscribe' % (base_url,),
            }

            footer = """
                        <div width="590" style="min-width: 590px; background-color: #F1F1F1; color: #454748; padding: 8px; border-collapse:separate;">
                            <div style="text-align: center; font-size: 12px;">
                                <a href=%(group_url)s>%(maillist)s</a> | %(post_to)s: %(mailto)s | <a href=%(unsub_url)s>%(unsub)s</a>
                            </div>
                        </div>
                    """ % vals
            body = tools.append_content_to_html(self.body, footer, plaintext=False)
            return body
        else:
            return super(MailMail, self)._send_prepare_body()
