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

from openerp.osv import osv, fields


class mail_message(osv.osv):
    _inherit = "mail.message"
    _columns = {
        'website_published': fields.boolean('Publish', help="Publish on the website as a blog"),
    }


class mail_group(osv.Model):
    _inherit = 'mail.group'

    def get_public_message_ids(self, cr, uid, domain=[], context=None):
        mail_group_ids = self.search(cr, uid, [('public', '=', 'public')], order="create_date", context=context)
        domain += [ ("type", "in", ['comment']),
                    ("parent_id", "=", False),
                    ("model", "=", 'mail.group'), ("res_id", "in", mail_group_ids)]
        return self.pool.get('mail.message').search(cr, uid, domain, context=context)
