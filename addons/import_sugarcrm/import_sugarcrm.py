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
import sugar
import tools
from tools.translate import _

class import_sugarcrm(osv.osv):
     """Import SugarCRM DATA"""

     _name = "import.sugarcrm"
     _description = __doc__
     _columns = {
        'mod_name':fields.selection([
            ('lead','Leads'),
            ('opportunity','Opportunities'),
            ('accounts','Accounts'),
            ('contact','Contacts'),
        ],'Module Name', help="Module Name is used to specify which Module data want to Import"),
     }

     def import_data(self, cr, uid, ids,context=None):
       if not context:
        context={}
       lead_pool = self.pool.get("crm.lead")
       for current in self.browse(cr, uid, ids):
        if current.mod_name == 'lead' or current.mod_name == 'opportunity':
          module_name = 'crm'

        elif current.mod_name == "accounts":
          module_name = 'account'
        ids = self.pool.get("ir.module.module").search(cr, uid, [("name", '=',
           module_name), ('state', '=', 'installed')])
        if not ids:
           raise osv.except_osv(_('Error !'), _('Please  Install %s Module') % (module_name))

       if current.mod_name == 'lead':
           sugar_name = "Leads"
       elif current.mod_name == 'opportunity':
           sugar_name="Opportunities"
       elif current.mod_name == 'accounts':
           sugar_name="Accounts"
       elif current.mod_name == 'contact':
           sugar_name="Contacts"

       sugar_data = sugar.test(sugar_name)
       for sugar_val in sugar_data:
           if sugar_name == "Leads":
               lead_pool.create(cr, uid, {'name': sugar_val.get("first_name"), 'email_from': sugar_val.get("email1"), 'phone': sugar_val.get("phone_work"), 'mobile': sugar_val.get("phone_mobile"), 'write_date':sugar_val.get("date_modified"), 'user_id':sugar_val.get("created_by"), 'partner_name':sugar_val.get("title"), 'city':sugar_val.get("primary_address_city")})

       return {}

import_sugarcrm()





