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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

import base64

from osv import osv, fields
from osv.orm import except_orm
from tools import config
import urlparse

import os

class document_configuration_wizard(osv.osv_memory):

    _name='document.configuration.wizard'
    _description = 'Auto Directory Configuration'
    _inherit = 'res.config'
    _rec_name = 'host'
    _columns = {
        'host': fields.char('Address', size=64,
                            help="Server address or IP and port to which users should connect to for DMS access", 
                            required=True),
    }

    _defaults = {
        'host': config.get('ftp_server_host', 'localhost') + ':' + config.get('ftp_server_port', '8021'),
    }

    def execute(self, cr, uid, ids, context=None):
        conf = self.browse(cr, uid, ids[0], context)
        obj=self.pool.get('document.directory')
        objid=self.pool.get('ir.model.data')

        if self.pool.get('sale.order'):
            id = objid._get_id(cr, uid, 'document', 'dir_sale_order_all')
            id = objid.browse(cr, uid, id, context=context).res_id
            mid = self.pool.get('ir.model').search(cr, uid, [('model','=','sale.order')])
            obj.write(cr, uid, [id], {
                'type':'ressource',
                'ressource_type_id': mid[0],
                'domain': '[]',
            })
            aid = objid._get_id(cr, uid, 'sale', 'report_sale_order')
            aid = objid.browse(cr, uid, aid, context=context).res_id

            self.pool.get('document.directory.content').create(cr, uid, {
                'name': "Print Order",
                'suffix': "_print",
                'report_id': aid,
                'extension': '.pdf',
                'include_name': 1,
                'directory_id': id,
            })
            id = objid._get_id(cr, uid, 'document', 'dir_sale_order_quote')
            id = objid.browse(cr, uid, id, context=context).res_id
            obj.write(cr, uid, [id], {
                'type':'ressource',
                'ressource_type_id': mid[0],
                'domain': "[('state','=','draft')]",
            })

        if self.pool.get('product.product'):
            id = objid._get_id(cr, uid, 'document', 'dir_product')
            id = objid.browse(cr, uid, id, context=context).res_id
            mid = self.pool.get('ir.model').search(cr, uid, [('model','=','product.product')])
            obj.write(cr, uid, [id], {
                'type':'ressource',
                'ressource_type_id': mid[0],
            })

        if self.pool.get('stock.location'):
            aid = objid._get_id(cr, uid, 'stock', 'report_product_history')
            aid = objid.browse(cr, uid, aid, context=context).res_id

            self.pool.get('document.directory.content').create(cr, uid, {
                'name': "Product Stock",
                'suffix': "_stock_forecast",
                'report_id': aid,
                'extension': '.pdf',
                'include_name': 1,
                'directory_id': id,
            })

        if self.pool.get('account.analytic.account'):
            id = objid._get_id(cr, uid, 'document', 'dir_project')
            id = objid.browse(cr, uid, id, context=context).res_id
            mid = self.pool.get('ir.model').search(cr, uid, [('model','=','account.analytic.account')])
            obj.write(cr, uid, [id], {
                'type':'ressource',
                'ressource_type_id': mid[0],
                'domain': '[]',
                'ressource_tree': 1
        })

        # Update the action for FTP browse.
        aid = objid._get_id(cr, uid, 'document_ftp', 'action_document_browse')
        aid = objid.browse(cr, uid, aid, context=context).res_id
        self.pool.get('ir.actions.url').write(cr, uid, [aid], {'url': 'ftp://'+(conf.host or 'localhost:8021')+'/'})
document_configuration_wizard()
