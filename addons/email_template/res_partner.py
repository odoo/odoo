# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2011 OpenERP S.A. <http://openerp.com>
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

from openerp.osv import fields, osv

class res_partner(osv.osv):
    """Inherit res.partner to add a generic opt-out field that can be used
       to restrict usage of automatic email templates.
       This field is unused by default. """
    _inherit = 'res.partner'

    _columns = {
        'opt_out': fields.boolean('Opt-Out',
            help="If opt-out is checked, this contact has refused to receive emails for mass mailing and marketing campaign. "
                    "Filter 'Available for Mass Mailing' allows users to filter the partners when performing mass mailing."),
    }

    _defaults = {
        'opt_out': False,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
