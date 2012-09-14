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

import tools
from osv import osv


class mail_mail_portal(osv.Model):
    """ Update of mail_mail class, to add the signin URL to notifications.
    """
    _name = 'mail.mail'
    _inherit = ['mail.mail']

    def _generate_signin_url(self, cr, uid, partner_id, portal_group_id, key, context=None):
        """ Generate the signin url """
        base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url', default='', context=context)
        return base_url + '/login?action=signin&partner_id=%s&group=%s&key=%s' % (partner_id, portal_group_id, key)

    def send_get_mail_body(self, cr, uid, mail, partner=None, context=None):
        """ Return a specific ir_email body. The main purpose of this method
            is to be inherited by Portal, to add a link for signing in, in
            each notification email a partner receives.

            :param mail: mail.mail browse_record
            :param partner: browse_record of the specific recipient partner
        """
        if partner:
            portal_ref = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'portal', 'portal_group')
            portal_id = portal_ref and portal_ref[1] or False
            url = self._generate_signin_url(cr, uid, partner.id, portal_id, 1234, context=context)
            body = tools.append_content_to_html(mail.body_html, url)
            return body
        else:
            return super(mail_mail_portal, self).send_get_mail_body(cr, uid, mail, partner=partner, context=context)
