# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_mrp_wo_tablet_timer = fields.Boolean("Timer", implied_group="mrp_workorder.group_mrp_wo_tablet_timer")
    group_mrp_wo_shop_floor = fields.Boolean("Shop Floor", implied_group="mrp_workorder.group_mrp_wo_shop_floor")

    def set_values(self):
        super().set_values()
        if not self.env.user.has_group('mrp.group_mrp_manager'):
            return
        register_byproducts = self.env.ref('mrp_workorder.test_type_register_byproducts').sudo()
        if register_byproducts.active != self.group_mrp_byproducts:
            register_byproducts.active = self.group_mrp_byproducts
