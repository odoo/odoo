# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2009 P. Christeas. All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import netsvc
from osv import osv, fields

class res_partner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
        'vat_taxauth': fields.many2one('account.fiscalgr.tauth','Tax authority', 
		domain=[('country_id','=','country_id')],
		help="Select the local tax service branch, where the partner is registered."),
	'vat_occup': fields.many2one('account.fiscalgr.occup','VAT Occupation', 
		help="Select the corresponding occupation of the partner, as registered with tax authorities."),
    }

res_partner()

#eof
