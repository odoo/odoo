# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2011 OpenERP S.A (<http://www.openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import SUPERUSER_ID
from openerp.osv import osv
from openerp.osv.orm import except_orm
from openerp.tools import append_content_to_html
from openerp.tools.translate import _


class mail_mail(osv.Model):
    """ Update of mail_mail class, to add the signin URL to notifications. """
    _inherit = 'mail.mail'

    def send_get_mail_body(self, cr, uid, mail, partner=None, context=None):
        """ add a signin link inside the body of a mail.mail
            :param mail: mail.mail browse_record
            :param partner: browse_record of the specific recipient partner
            :return: the resulting body_html
        """
        partner_obj = self.pool.get('res.partner')
        body = mail.body_html
        if partner:
            contex_signup = dict(context or {}, signup_valid=True)
            partner = partner_obj.browse(cr, SUPERUSER_ID, partner.id, context=contex_signup)
            text = _("""<p>Access your messages and personal documents through <a href="%s">our Customer Portal</a></p>""") % partner.signup_url
            # partner is an user: add a link to the document if read access
            if partner.user_ids and mail.model and mail.res_id \
                    and self.check_access_rights(cr, partner.user_ids[0].id, 'read', raise_exception=False):
                related_user = partner.user_ids[0]
                try:
                    self.pool.get(mail.model).check_access_rule(cr, related_user.id, [mail.res_id], 'read', context=context)
                    url = partner_obj._get_signup_url_for_action(cr, related_user.id, [partner.id], action='', res_id=mail.res_id, model=mail.model, context=context)[partner.id]
                    text = _("""<p>Access this document <a href="%s">directly in OpenERP</a></p>""") % url
                except except_orm, e:
                    pass
            body = append_content_to_html(body, ("<div><p>%s</p></div>" % text), plaintext=False)
        return body
