# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv


class pos_config(osv.osv):
    _inherit = 'pos.config'
    _columns = {
        'loyalty_id': fields.many2one('loyalty.program', 'Loyalty Program', help='The loyalty program used by this point_of_sale'),
    }
