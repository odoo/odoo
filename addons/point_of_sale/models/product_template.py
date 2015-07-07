# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools.translate import _



class product_template(osv.osv):
    _inherit = 'product.template'

    _columns = {
        'available_in_pos': fields.boolean('Available in the Point of Sale', help='Check if you want this product to appear in the Point of Sale'), 
        'to_weight' : fields.boolean('To Weigh With Scale', help="Check if the product should be weighted using the hardware scale integration"),
        'pos_categ_id': fields.many2one('pos.category','Point of Sale Category', help="Those categories are used to group similar products for point of sale."),
    }

    _defaults = {
        'to_weight' : False,
        'available_in_pos': True,
    }

    def unlink(self, cr, uid, ids, context=None):
        product_ctx = dict(context or {}, active_test=False)
        if self.search_count(cr, uid, [('id', 'in', ids), ('available_in_pos', '=', True)], context=product_ctx):
            if self.pool['pos.session'].search_count(cr, uid, [('state', '!=', 'closed')], context=context):
                raise osv.except_osv(_('Error!'),
                    _('You cannot delete a product saleable in point of sale while a session is still opened.'))
        return super(product_template, self).unlink(cr, uid, ids, context=context)
