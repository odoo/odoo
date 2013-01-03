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

from urllib import urlencode
from urlparse import urljoin

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
        body = super(mail_mail, self).send_get_mail_body(cr, uid, mail, partner, context=context)
        if partner:
            context = dict(context or {}, signup_valid=True)
            partner = self.pool.get('res.partner').browse(cr, SUPERUSER_ID, partner.id, context=context)
            text = ''
            # private message
            if not mail.model or not mail.res_id:
                text = _("""<p>Access your messages through <a href="%s">our Customer Portal</a></p>""") % partner.signup_url
            # partner is also an user: add a link if read access to the document
            elif partner.user_ids and self.check_access_rights(cr, partner.user_ids[0].id, 'read', raise_exception=False):
                related_user = partner.user_ids[0]
                try:
                    self.pool.get(mail.model).check_access_rule(cr, related_user.id, [mail.res_id], 'read', context=context)
                    base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
                    url_params = {
                        'model': mail.model,
                        'id': mail.res_id,
                    }
                    url = urljoin(base_url, "?#%s" % (urlencode(url_params)))
                    text = _("""<p>Access this document <a href="%s">directly in OpenERP</a></p>""") % url
                except except_orm, e:
                    text = _("""<p>Access your messages through <a href="%s">our Customer Portal</a></p>""") % partner.signup_url
            # partner not user
            else:
                text = _("""<p>Access your messages through <a href="%s">our Customer Portal</a></p>""") % partner.signup_url
            body = append_content_to_html(body, ("<div><p>%s</p></div>" % text), plaintext=False)
        return body
