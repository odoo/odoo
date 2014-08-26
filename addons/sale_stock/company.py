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

from openerp.osv import fields, osv

class company(osv.osv):
    _inherit = 'res.company'
    _columns = {
        'security_lead': fields.float(
            'Security Days', required=True,
            help="Margin of error for dates promised to customers. "\
                 "Products will be scheduled for procurement and delivery "\
                 "that many days earlier than the actual promised date, to "\
                 "cope with unexpected delays in the supply chain."),
    }
    _defaults = {
        'security_lead': 0.0,
    }
