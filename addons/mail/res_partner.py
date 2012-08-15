# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from osv import osv

class res_partner_mail(osv.Model):
    """ Inherits partner and adds CRM information in the partner form """
    _name = "res.partner"
    _inherit = ['res.partner', 'mail.thread']

    def message_search_get_domain(self, cr, uid, ids, context=None):
        """ Override of message_search_get_domain for partner discussion page.
            The purpose is to add messages directly sent to the partner. It also
            adds messages pushed to the related user, if any, using @login.
        """
        initial_domain = super(res_partner_mail, self).message_search_get_domain(cr, uid, ids, context=context)
        # to avoid models inheriting from res.partner
        if self._name != 'res.partner':
            return initial_domain
        # add message linked to the partner
        search_domain = ['|'] + initial_domain + ['|', ('partner_id', 'in', ids), ('partner_ids', 'in', ids)]
        # if partner is linked to a user: find @login
        res_users_obj = self.pool.get('res.users')
        user_ids = res_users_obj.search(cr, uid, [('partner_id', 'in', ids)], context=context)
        for user in res_users_obj.browse(cr, uid, user_ids, context=context):
            search_domain = ['|'] + search_domain + ['|', ('body_text', 'like', '@%s' % (user.login)), ('body_html', 'like', '@%s' % (user.login))]
        return search_domain
    _columns = {
        'notification_email_pref': fields.selection([
            ('all', 'All feeds'),
            ('comment', 'Comments and emails'),
            ('none', 'Never')
            ], 'Receive Feeds by Email', required=True,
            help="Choose in which case you want to receive an email when you "\
                  "receive new feeds."),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
