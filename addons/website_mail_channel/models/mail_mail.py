# -*- coding: utf-8 -*-

from openerp.osv import osv
from openerp import tools
from openerp.tools.translate import _
from openerp.addons.website.models.website import slug


class MailMail(osv.Model):
    _inherit = 'mail.mail'

    def send_get_mail_body(self, cr, uid, ids, partner=None, context=None):
        """ Short-circuit parent method for mail groups, replace the default
            footer with one appropriate for mailing-lists."""
        # TDE: temporary addition (mail was parameter) due to semi-new-API
        mail = self.browse(cr, uid, ids[0], context=context)

        if mail.model == 'mail.channel' and mail.res_id:
            # no super() call on purpose, no private links that could be quoted!
            channel = self.pool['mail.channel'].browse(cr, uid, mail.res_id, context=context)
            base_url = self.pool['ir.config_parameter'].get_param(cr, uid, 'web.base.url')
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
            body = tools.append_content_to_html(mail.body, footer, container_tag='div')
            return body
        else:
            return super(MailMail, self).send_get_mail_body(cr, uid, ids, partner=partner, context=context)
