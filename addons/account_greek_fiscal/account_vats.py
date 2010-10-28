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

class account_fiscalgr_tauth(osv.osv):
  _name = 'account.fiscalgr.tauth'
  _inherit = ''
  _columns = {
      'name': fields.char('Name',size=120,required=True ),
      'country_id': fields.many2one('res.country', 'Country', required=True),
      'code': fields.char('Code',size=30),
      'descr': fields.text('Description',help="Any notes for this authority"),
  }
  _defaults = {
  }

account_fiscalgr_tauth()

class account_fiscalgr_occup(osv.osv):
  _name = 'account.fiscalgr.occup'
  _inherit = ''
  _columns = {
      'name': fields.char('Name',size=120,required=True ),
      'code': fields.char('Code',size=30),
      'descr': fields.text('Description'),
  }
  _defaults = {
  }

account_fiscalgr_occup()

#eof
