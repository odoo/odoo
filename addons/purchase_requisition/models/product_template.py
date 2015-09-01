# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv


class product_template(osv.osv):
    _inherit = 'product.template'

    _columns = {
        'purchase_requisition': fields.selection(
            [('rfq', 'Create a draft purchase order'),
             ('tenders', 'Propose a call for tenders')],
            string='Procurement',
            help="Check this box to generate Call for Tenders instead of generating "
                 "requests for quotation from procurement."),
    }

    _defaults = {
        'purchase_requisition': 'rfq',
    }
