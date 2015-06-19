# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv


class res_company(osv.osv):
    _inherit = 'res.company'

    _columns = {
        'siret': fields.related('partner_id', 'siret', type='char', relation='res.partner', string='Siret'),
        'ape': fields.char('APE'),
    }
