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

from osv import osv, fields

class res_partner_mail(osv.Model):
    """ Update partner to add a field about notification preferences """
    _name = "res.partner"
    _inherit = ['res.partner', 'mail.thread']

    _columns = {
        'notification_email_pref': fields.selection([
            ('all', 'All feeds'),
            ('comment', 'Comments and emails'),
            ('none', 'Never')
            ], 'Receive Feeds by Email', required=True,
            help="Choose in which case you want to receive an email when you "\
                  "receive new feeds."),
    }

    _defaults = {
        'notification_email_pref': lambda *args: 'comment'
    }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
