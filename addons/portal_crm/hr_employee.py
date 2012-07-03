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

from osv import osv, fields



class hr_employee(osv.osv):
    _description = "Portal CRM Employee"
    _inherit = 'hr.employee'

    """
    ``visibility``: defines if the employee appears on the portal's contact page
                    - 'public' means the employee will appear for everyone (anonymous)
                    - 'portal' means the employee will appear for portal users only
                    - 'private' means the employee won't appear
    """
    _columns = {
        'visibility': fields.selection([('public', 'Public'),('portal', 'Portal'),('private', 'Private')],
            string='Visibility', help='Employee\'s visibility in the portal\'s contact page'),
    }
    _defaults = {
        'visibility': 'private',
    }
