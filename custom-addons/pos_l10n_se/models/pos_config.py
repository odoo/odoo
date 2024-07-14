# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class PosConfig(models.Model):
    _inherit = "pos.config"

    iface_sweden_fiscal_data_module = fields.Many2one(
        "iot.device",
        domain="[('type', '=', 'fiscal_data_module'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )

    def _compute_iot_device_ids(self):
        super(PosConfig, self)._compute_iot_device_ids()
        for config in self:
            if config.is_posbox:
                config.iot_device_ids += config.iface_sweden_fiscal_data_module

    def _check_before_creating_new_session(self):
        if self.iface_sweden_fiscal_data_module:
            self._check_pos_settings_for_sweden()
        return super()._check_before_creating_new_session()

    def _check_pos_settings_for_sweden(self):
        if self.iface_sweden_fiscal_data_module and not self.company_id.company_registry:
            raise ValidationError(
                _("The company require a company registry when you are using the blackbox.")
            )
        if self.iface_sweden_fiscal_data_module and not self.company_id.vat:
            raise ValidationError(
                _("The company require a VAT number when you are using the blackbox.")
            )
        if self.iface_sweden_fiscal_data_module and not self.cash_control:
            raise ValidationError(
                _("You cannot use the sweden blackbox without cash control.")
            )
        if self.iface_sweden_fiscal_data_module and self.iface_splitbill:
            raise ValidationError(
                _("You cannot use the sweden blackbox with the bill splitting setting.")
            )

    def get_order_sequence_number(self):
        return self.sequence_id.number_next_actual
