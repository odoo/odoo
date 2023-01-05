# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class BoothBatchEventConfigurator(models.TransientModel):
    _name = 'event.event.booth.configurator.batch'
    _description = 'Event booth batch Configurator'

    configurable_booth_event_ids = fields.One2many('event.booth.editor.line', 'editor_id', string="Configurable Event ids")
    sale_order_id = fields.Many2one('sale.order', 'Sales Order', required=True, ondelete='cascade')

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if not res.get('sale_order_id'):
            sale_order_id = res.get('sale_order_id', self._context.get('active_id'))
            res['sale_order_id'] = sale_order_id
        sale_order = self.env['sale.order'].browse(res.get('sale_order_id'))
        res['configurable_booth_event_ids'] = [
            [0, 0, {
                'event_id': so_line.event_id.id,
                'event_booth_ids': so_line.event_booth_ids.ids,
                'event_booth_category_id': so_line.event_booth_category_id.id,
                'product_id': so_line.product_id,
                'order_id': sale_order,
                'sale_order_line_id':so_line,
            }]
            for so_line in sale_order.order_line
            for __ in range(int(so_line.product_uom_qty))
            if so_line.product_type == 'event_booth'
        ]
        return self._convert_to_write(res)

    def action_configure(self):
        self.ensure_one()
        for configurable_booth_event_id in self.configurable_booth_event_ids:
            configurable_booth_event_id._get_event_data()
        return {'type': 'ir.actions.act_window_close'}
