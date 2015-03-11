# -*- coding: utf-8 -*-

from openerp import api, models, _
from openerp import SUPERUSER_ID

class Mail(models.Model):
    """ Update of mail_mail class, to add the signin URL to notifications. """
    _inherit = 'mail.mail'

    @api.v7
    def _get_partner_access_link(self, cr, uid, mail, partner=None, context=None):
        """ Generate URLs for links in mails:
            - partner is not an user: signup_url
            - partner is an user: fallback on classic URL
        """
        if context is None:
            context = {}
        Partner = self.pool['res.partner']
        if partner and not partner.user_ids:
            contex_signup = dict(context, signup_valid=True)
            signup_url = Partner._get_signup_url_for_action(cr, SUPERUSER_ID, [partner.id],
                                                                action='mail.action_mail_redirect',
                                                                model=mail.model, res_id=mail.res_id,
                                                                context=contex_signup)[partner.id]
            return ", <span class='oe_mail_footer_access'><small>%(access_msg)s <a style='color:inherit' href='%(portal_link)s'>%(portal_msg)s</a></small></span>" % {
                'access_msg': _('access directly to'),
                'portal_link': signup_url,
                'portal_msg': '%s %s' % (context.get('model_name', ''), mail.record_name) if mail.record_name else _('your messages '),
            }
        else:
            return super(Mail, self)._get_partner_access_link(cr, uid, mail, partner=partner, context=context)

    @api.v8
    def _get_partner_access_link(self, partner=None):
        return self._model._get_partner_access_link(self._cr, self._uid, self, partner=partner)