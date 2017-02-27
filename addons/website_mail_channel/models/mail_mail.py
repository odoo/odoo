# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, tools, _
from odoo.addons.website.models.website import slug


class MailMail(models.Model):
    _inherit = 'mail.mail'

    @api.multi
    def send_get_mail_body(self, partner=None):
        """ Short-circuit parent method for mail groups, replace the default
            footer with one appropriate for mailing-lists."""
        if self.model == 'mail.channel' and self.res_id:
            # no super() call on purpose, no private links that could be quoted!
            channel = self.env['mail.channel'].browse(self.res_id)
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            vals = {
                'maillist': _('Mailing-List'),
                'post_to': _('Post to'),
                'unsub': _('Unsubscribe'),
                'mailto': 'mailto:%s@%s' % (channel.alias_name, channel.alias_domain),
                'group_url': '%s/groups/%s' % (base_url, slug(channel)),
                'unsub_url': '%s/groups?unsubscribe' % (base_url,),
            }
            footer = """_______________________________________________
                        %(maillist)s: %(group_url)s
                        %(post_to)s: %(mailto)s
                        %(unsub)s: %(unsub_url)s
                    """ % vals
            body = tools.append_content_to_html(self.body, footer, container_tag='div')
            return body
        else:
            return super(MailMail, self).send_get_mail_body(partner=partner)
