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
from osv import fields, osv
import pooler
import pytz


class specify_product_terminology(osv.osv_memory):
    _name = 'specify.product.terminology'
    _inherit = 'res.config'
    _columns = {
        'partner': fields.selection([('customers','Customers'),
                                  ('clients','Clients'),
                                  ('members','Members'),
                                  ('patients','Patients'),
                                  ('partners','Partners'),
                                  ('donors','Donors'),
                                  ('guests','Guests'),
                                  ('tenants','Tenants')
                                  ],
                                 'Choose how to call a Customer', required=True ),
                                 
        'products' : fields.char('Choose how to call a Product', size=64),
        
    }
    _defaults={
               'partner' :'partners',
    }
    
specify_product_terminology()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
