# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class IrModelFields(models.Model):
    _inherit = "ir.model.fields"

    @api.multi
    def unlink(self):
        carriers = self.env['ir.module.module'].search_read([
            ('name', 'like', 'delivery_%')
        ], ['name'])
        carriers = [s['name'].split('_')[1] for s in carriers]
        if carriers and self.name.find('_') >= 0:
            name = self.name.split('_')[0]
            if name in carriers:
                self.env['delivery.carrier'].search([
                    ('delivery_type', '=', name)
                ]).write({'delivery_type': 'fixed'})
        return super(IrModelFields, self).unlink()
