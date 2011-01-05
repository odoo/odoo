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

import netsvc
from osv import fields, osv
from tools.translate import _

class stock_ups(osv.osv_memory):
    _name = "stock.ups"
    _description = "Stock ups"

    def ups_save(self, cr, uid, ids, context=None):
        return {
            'name': False,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.ups.final',
            'type': 'ir.actions.act_window',
            'target':'new',
        }

    def ups_upload(self, cr, uid, ids, context=None):
        return {
            'name': False,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.ups.upload',
            'type': 'ir.actions.act_window',
            'target':'new',
        }

    _columns = {
        'weight': fields.float('Lot weight', required=True),
    }

    _defaults = {
        'weight': lambda *a: 3.0,
    }
stock_ups()

class stock_ups_final(osv.osv_memory):
    _name = "stock.ups.final"
    _description = "Stock ups final"

    def create_xmlfile(self, cr, uid, ids, context=None):
        """ Creates xml report file.
        @return: xml file
        """
        data={}
        report = netsvc._group['report']['report.stock.move.lot.ups_xml']
        data['report_type'] = 'raw'
        return {'xmlfile' : report.create(uid, context['active_id'], ids, {})}

    _columns = {
        'xmlfile': fields.binary('XML File'), 
    }

stock_ups_final()

class stock_ups_upload(osv.osv_memory):
    _name = "stock.ups.upload"
    _description = "Stock ups upload"

    def upload_xmlfile(self, cr, uid, ids, context=None):
        """ Uploads xml report file.
        @return: 
        """
        data={}
        report = netsvc._group['report']['report.stock.move.lot.ups_xml']
        data['report_type'] = 'raw'
        fp = file('/tmp/test.xml', 'w').write(report.create(uid, context['active_id'], ids, {}))
        return {'type': 'ir.actions.act_window_close'}

stock_ups_upload()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

