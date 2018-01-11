# -*- coding: utf-8 -*-

from openerp.osv import osv
from openerp import tools
from openerp.tools.translate import _
from openerp.tools.safe_eval import safe_eval as eval
from openerp.addons.website.models.website import slug

class MailGroup(osv.Model):
    _inherit = 'mail.group'

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


class MailMail(osv.Model):
    _inherit = 'mail.mail'

    def send_get_mail_body(self, cr, uid, mail, partner=None, context=None):
        """ Short-circuit parent method for mail groups, replace the default
            footer with one appropriate for mailing-lists."""

        if mail.model == 'mail.group' and mail.res_id:
            # no super() call on purpose, no private links that could be quoted!
            group = self.pool['mail.group'].browse(cr, uid, mail.res_id, context=context)
            base_url = self.pool['ir.config_parameter'].get_param(cr, uid, 'web.base.url')
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
            return super(MailMail, self).send_get_mail_body(cr, uid, mail,
                                                            partner=partner,
                                                            context=context)
