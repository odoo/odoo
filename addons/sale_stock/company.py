# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv

class company(osv.osv):
    _inherit = 'res.company'
    _columns = {
        'security_lead': fields.float(
            'Sales Safety Days', required=True,
            help="Margin of error for dates promised to customers. "\
                 "Products will be scheduled for procurement and delivery "\
                 "that many days earlier than the actual promised date, to "\
                 "cope with unexpected delays in the supply chain."),
    }
    _defaults = {
        'security_lead': 0.0,
    }
