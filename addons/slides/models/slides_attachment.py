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
import openerp
from openerp.osv import fields, osv


class slides_attachment(osv.osv):	
    _inherit = 'ir.attachment'

    _columns = {
        'is_slide': fields.boolean('Is Slide')
    }
    _order = "id desc"
   
   
    def create(self, cr, uid, values, context=None):        
        values['is_slide']=True
        values['url']="/slides/"+values['datas_fname']
        return super(slides_attachment, self).create(cr, uid, values, context)
        
    def read(self, cr, uid, ids, fields_to_read=None, context=None, load=None):
        ids = self.search(cr,uid,[('is_slide','=','TRUE')],context=context)
        #print ">>>>>>>>>>>>>>>>>>>>>>>>>>",ids
        return super(slides_attachment, self).read(cr, uid, ids, fields_to_read=None, context=None, load=None)
        
        