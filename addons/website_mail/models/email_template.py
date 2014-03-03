# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014-Today OpenERP SA (<http://www.openerp.com>).
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
from openerp.tools.translate import _


class EmailTemplate(osv.Model):
    _inherit = 'email.template'

    def _get_website_link(self, cr, uid, ids, name, args, context=None):
        return dict((id, _('<a href="website_mail/email_designer/%s">Edit in Website</a>') % id) for id in ids)

    _columns = {
        'website_link': fields.function(
            _get_website_link, type='text',
            string='Website Link',
            help='Link to the website',
        ),
    }
