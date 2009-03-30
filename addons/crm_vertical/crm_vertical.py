# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
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

import time
import tools
from osv import fields,osv,orm
import os
import mx.DateTime
import base64
from tools.translate import _

# here need to implement inheritance on osv_memory object. after that, it will work well.
class crm_menu_config_wizard(osv.osv_memory):
    _inherit='crm.menu.config_wizard'
    def action_create(self, cr, uid, ids, *args):
        res=super(crm_menu_config_wizard, self).action_create(cr, uid, ids, *args)
        for res in self.read(cr,uid,ids):
            res.__delitem__('id')
            for section in res :
                if res[section]:
                    file_name = 'crm_'+section+'_vertical_view.xml'
                    try:
                        tools.convert_xml_import(cr, 'crm_configuration', tools.file_open(os.path.join('crm_vertical',file_name )),  {}, 'init', *args)
                    except Exception, e:
                        raise osv.except_osv(_('Error !'), str(e))
        return res

crm_menu_config_wizard()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
