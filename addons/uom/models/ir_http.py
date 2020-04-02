
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        res = super().session_info()
        uoms = {}
        if request.session.uid:
            for uom in self.env['uom.uom'].search_read([], ['name', 'decimal_places', 'rounding']):
                uoms[uom['id']] = {
                    'name': uom['name'],
                    'decimal_places': uom['decimal_places'],
                    'rounding': uom['rounding'],
                }
        res['uoms'] = uoms
        return res
