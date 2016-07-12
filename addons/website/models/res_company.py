# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import openerp
from openerp.osv import osv, fields


class res_company(osv.osv):

    _inherit = "res.company"

    def google_map_img(self, cr, uid, ids, zoom=8, width=298, height=298, context=None):
        partner = self.browse(cr, openerp.SUPERUSER_ID, ids[0], context=context).partner_id
        return partner and partner.google_map_img(zoom, width, height, context=context) or None

    def google_map_link(self, cr, uid, ids, zoom=8, context=None):
        partner = self.browse(cr, openerp.SUPERUSER_ID, ids[0], context=context).partner_id
        return partner and partner.google_map_link(zoom, context=context) or None
