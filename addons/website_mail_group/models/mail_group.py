# -*- coding: utf-8 -*-

from openerp import api, models, tools, _
from openerp.tools.safe_eval import safe_eval as eval
from openerp.addons.website.models.website import slug


class MailGroup(models.Model):
    _inherit = 'mail.group'

    @api.multi
    def message_get_email_values(self, notif_mail=None):
        res = super(MailGroup, self).message_get_email_values(notif_mail=notif_mail)[0]
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


class MailMail(models.Model):
    _inherit = 'mail.mail'

    @api.model
    def send_get_mail_body(self, mail, partner=None):
        """ Short-circuit parent method for mail groups, replace the default
            footer with one appropriate for mailing-lists."""

        if mail.model == 'mail.group' and mail.res_id:
            # no super() call on purpose, no private links that could be quoted!
            group = self.env['mail.group'].browse(mail.res_id)
            base_url = self.env['ir.config_parameter'].get_param('web.base.url')
            vals = {
                'maillist': _('Mailing-List'),
                'post_to': _('Post to'),
                'unsub': _('Unsubscribe'),
                'mailto': 'mailto:%s@%s' % (group.alias_name, group.alias_domain),
                'group_url': '%s/groups/%s' % (base_url, slug(group)),
                'unsub_url': '%s/groups?unsubscribe' % (base_url,),
            }
            footer = """_______________________________________________
                        %(maillist)s: %(group_url)s
                        %(post_to)s: %(mailto)s
                        %(unsub)s: %(unsub_url)s
                    """ % vals
            body = tools.append_content_to_html(mail.body, footer, container_tag='div')
            return body
        else:
            return super(MailMail, self).send_get_mail_body(mail, partner=partner)
