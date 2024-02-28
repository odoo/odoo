# -*- coding: utf-8 -*-

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def _get_floors_domain(self):
        return ['|', ('pos_config_id', 'in', self.pos_config_id.ids), ('pos_config_id', '=', False)]

    pos_floor_ids = fields.One2many(related='pos_config_id.floor_ids', readonly=False, domain=lambda self: self._get_floors_domain())
    pos_iface_orderline_notes = fields.Boolean(compute='_compute_pos_module_pos_restaurant', store=True, readonly=False)
    pos_iface_printbill = fields.Boolean(compute='_compute_pos_module_pos_restaurant', store=True, readonly=False)
    pos_iface_splitbill = fields.Boolean(compute='_compute_pos_module_pos_restaurant', store=True, readonly=False)
    pos_is_order_printer = fields.Boolean(compute='_compute_pos_module_pos_restaurant', store=True, readonly=False)
    pos_is_table_management = fields.Boolean(compute='_compute_pos_module_pos_restaurant', store=True, readonly=False)
    pos_printer_ids = fields.Many2many(related='pos_config_id.printer_ids', readonly=False)
    pos_set_tip_after_payment = fields.Boolean(compute='_compute_pos_set_tip_after_payment', store=True, readonly=False)

    @api.depends('pos_module_pos_restaurant', 'pos_config_id')
    def _compute_pos_module_pos_restaurant(self):
        for res_config in self:
            if not res_config.pos_module_pos_restaurant:
                res_config.update({
                    'pos_iface_orderline_notes': False,
                    'pos_iface_printbill': False,
                    'pos_iface_splitbill': False,
                    'pos_is_order_printer': False,
                    'pos_is_table_management': False,
                })
            else:
                res_config.update({
                    'pos_iface_orderline_notes': res_config.pos_config_id.iface_orderline_notes,
                    'pos_iface_printbill': res_config.pos_config_id.iface_printbill,
                    'pos_iface_splitbill': res_config.pos_config_id.iface_splitbill,
                    'pos_is_order_printer': res_config.pos_config_id.is_order_printer,
                    'pos_is_table_management': res_config.pos_config_id.is_table_management,
                })

    @api.depends('pos_iface_tipproduct', 'pos_config_id')
    def _compute_pos_set_tip_after_payment(self):
        for res_config in self:
            if res_config.pos_iface_tipproduct:
                res_config.pos_set_tip_after_payment = res_config.pos_config_id.set_tip_after_payment
            else:
                res_config.pos_set_tip_after_payment = False
