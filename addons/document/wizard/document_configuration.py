# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv

class document_configuration(osv.osv_memory):
    _name='document.configuration'
    _description = 'Directory Configuration'
    _inherit = 'res.config'

    def execute(self, cr, uid, ids, context=None):
        dir_pool = self.pool.get('document.directory')
        data_pool = self.pool.get('ir.model.data')
        model_pool = self.pool.get('ir.model')
        content_pool = self.pool.get('document.directory.content')
        if self.pool.get('sale.order'):
            # Sale order
            dir_data_id = data_pool._get_id(cr, uid, 'document', 'dir_sale_order_all')
            if dir_data_id:
                sale_dir_id = data_pool.browse(cr, uid, dir_data_id, context=context).res_id
            else:
                sale_dir_id = data_pool.create(cr, uid, {'name': 'Sale Orders'})
            mid = model_pool.search(cr, uid, [('model','=','sale.order')])
            dir_pool.write(cr, uid, [sale_dir_id], {
                'type':'ressource',
                'ressource_type_id': mid[0],
                'domain': '[]',
            })
            # Qutation
            dir_data_id = data_pool._get_id(cr, uid, 'document', 'dir_sale_order_quote')
            if dir_data_id:
                quta_dir_id = data_pool.browse(cr, uid, dir_data_id, context=context).res_id
            else:
                quta_dir_id = data_pool.create(cr, uid, {'name': 'Sale Quotations'})

            dir_pool.write(cr, uid, [quta_dir_id], {
                'type':'ressource',
                'ressource_type_id': mid[0],
                'domain': "[('state','=','draft')]",
            })
            # Sale Order Report
            order_report_data_id = data_pool._get_id(cr, uid, 'sale', 'report_sale_order')
            if order_report_data_id:
                order_report_id = data_pool.browse(cr, uid, order_report_data_id, context=context).res_id

                content_pool.create(cr, uid, {
                    'name': "Print Order",
                    'suffix': "_print",
                    'report_id': order_report_id,
                    'extension': '.pdf',
                    'include_name': 1,
                    'directory_id': sale_dir_id,
                })

                content_pool.create(cr, uid, {
                    'name': "Print Quotation",
                    'suffix': "_print",
                    'report_id': order_report_id,
                    'extension': '.pdf',
                    'include_name': 1,
                    'directory_id': quta_dir_id,
                })


        if self.pool.get('product.product'):
            # Product
            dir_data_id = data_pool._get_id(cr, uid, 'document', 'dir_product')
            if dir_data_id:
                product_dir_id = data_pool.browse(cr, uid, dir_data_id, context=context).res_id
            else:
                product_dir_id = data_pool.create(cr, uid, {'name': 'Products'})

            mid = model_pool.search(cr, uid, [('model','=','product.product')])
            dir_pool.write(cr, uid, [product_dir_id], {
                'type':'ressource',
                'ressource_type_id': mid[0],
            })

        if self.pool.get('account.analytic.account'):
            # Project
            dir_data_id = data_pool._get_id(cr, uid, 'document', 'dir_project')
            if dir_data_id:
                project_dir_id = data_pool.browse(cr, uid, dir_data_id, context=context).res_id
            else:
                project_dir_id = data_pool.create(cr, uid, {'name': 'Projects'})

            mid = model_pool.search(cr, uid, [('model','=','account.analytic.account')])
            dir_pool.write(cr, uid, [project_dir_id], {
                'type':'ressource',
                'ressource_type_id': mid[0],
                'domain': '[]',
                'ressource_tree': 1
        })
