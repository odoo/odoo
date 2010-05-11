# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

from lxml import etree
from operator import itemgetter
from osv import fields, osv
import netsvc
import os
import pooler
import tools

class crm_installer(osv.osv_memory):
    _name = 'crm.installer'
    _inherit = 'res.config.installer'
    
    _columns = {
        'name': fields.char('Name', size=64), 
        'crm_helpdesk': fields.boolean('Helpdesk', help="Manages an Helpdesk service."), 
        'crm_fundraising': fields.boolean('Fundraising', help="This may help associations in their fund raising process and tracking."), 
        'crm_claim': fields.boolean('Claims', help="Manages the supplier and customers claims, including your corrective or preventive actions."), 
        'crm_caldav': fields.boolean('Calendar Synchronizing', help="Help you to synchronize the meetings with other calender clients(e.g.: Sunbird)."), 
        'sale_crm': fields.boolean('Opportunity to Quotation', help="This module relates sale to opportunity cases in the CRM."),
        'fetchmail': fields.boolean('Fetch Emails', help="Fetchmail Server."),
        'thunderbird': fields.boolean('Thunderbird', help="Thunderbird Interface."),  
    }
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(crm_installer, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar,submenu=False)
        #Checking sale module is installed or not
        cr.execute("SELECT * from ir_module_module where state='installed' and name = 'sale'")
        count = cr.fetchall()
        if count:
            doc = etree.XML(res['arch'])
            nodes = doc.xpath("//field[@name='sale_crm']")
            for node in nodes:
                node.set('invisible', '0')
            res['arch'] = etree.tostring(doc)
        return res

crm_installer()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
