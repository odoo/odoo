# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv


class product_template(osv.osv):
    _inherit = "product.template"
    _columns = {
        'project_id': fields.many2one('project.project', 'Project', ondelete='set null',),
        'auto_create_task': fields.boolean('Create Task Automatically', help="Tick this option if you want to create a task automatically each time this product is sold"),
    }

class product_product(osv.osv):
    _inherit = "product.product"

    def need_procurement(self, cr, uid, ids, context=None):
        for product in self.browse(cr, uid, ids, context=context):
            if product.type == 'service' and product.auto_create_task:
                return True
        return super(product_product, self).need_procurement(cr, uid, ids, context=context)
