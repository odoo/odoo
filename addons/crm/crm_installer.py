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
        'crm_fundraising': fields.boolean('Fund Raising Operations', help="This may help associations in their fund raising process and tracking."), 
        'crm_claim': fields.boolean('Claims', help="Manages the supplier and customers claims, including your corrective or preventive actions."), 
        'crm_caldav': fields.boolean('Calendar Synchronizing', help="Help you to synchronize the meetings with other calender clients(e.g.: Sunbird)."), 
        'sale_crm': fields.boolean('Sale CRM Stuff', help="This module relates sale to opportunity cases in the CRM. We suggest you to install this module if you installed both the sale and the crm modules"), 
    }

crm_installer()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
