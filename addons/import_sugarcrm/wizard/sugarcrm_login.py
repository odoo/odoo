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
from osv import fields, osv
from tools.translate import _
from import_sugarcrm import sugar

class sugarcrm_login(osv.osv):
    """SugarCRM Login"""

    _name = "sugarcrm.login"
    _description = __doc__
    _columns = {
        'username': fields.char('User Name', size=64, required=True),
        'password': fields.char('Password', size=24,required=True),
         'url' : fields.char('Service', size=264, required=True, help="Connection with Sugarcrm Using Soap Protocol Services and For that Path should be 'http://localhost/sugarcrm/soap.php' Format."),
    }
    _defaults = {
       'username' : 'tfr',
       'password' : 'a',
       'url':  "http://localhost/sugarcrm/soap.php"
    }

sugarcrm_login()
