# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv


class res_partner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
        'loyalty_points': fields.float('Loyalty Points', help='The loyalty points the user won as part of a Loyalty Program')
    }
