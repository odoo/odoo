# -*- coding: utf-8 -*-
##############################################################################
#
#   Copyright (C) 2013-2014 7Gates Interactive Technologies 
#                           <http://www.7gates.co>
#                 @author Erdem Uney
#   
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of the
#   License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import osv

class wizard_multi_charts_accounts(osv.osv_memory):
	_inherit='wizard.multi.charts.accounts'
	
	_defaults = {
		'code_digits' : 3,
	}
