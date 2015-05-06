# -*- coding: utf-8 -*-

from openerp import _, api, models


class MailMail(models.Model):
    """ Update of mail_mail class, to add the signin URL to notifications. """
    _inherit = 'mail.mail'

    @api.multi
    def _get_partner_access_link(self, partner=None):
        """ Generate URLs for links in mails:
            - partner is not an user: signup_url
            - partner is an user: fallback on classic URL
        """
        if partner and not partner.user_ids:
            signup_url = partner.with_context(signup_valid=True).sudo()._get_signup_url_for_action(action='mail.action_mail_redirect', model=self.model, res_id=self.res_id)[partner.id]
            return ", <span class='oe_mail_footer_access'><small>%(access_msg)s <a style='color:inherit' href='%(portal_link)s'>%(portal_msg)s</a></small></span>" % {
                'access_msg': _('access directly to'),
                'portal_link': signup_url,
                'portal_msg': '%s %s' % (self._context.get('model_name', ''), self.record_name) if self.record_name else _('your messages '),
            }
        else:
            return super(MailMail, self)._get_partner_access_link(partner=partner)
