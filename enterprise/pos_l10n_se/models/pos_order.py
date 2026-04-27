# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools.translate import _


class PosOrder(models.Model):
    _inherit = "pos.order"

    sweden_blackbox_signature = fields.Char(
        "Sweden Electronic signature",
        help="Electronic signature returned by the Fiscal Data Module",
        readonly=True,
    )
    sweden_blackbox_unit_id = fields.Char(readonly=True)
    sweden_blackbox_tax_category_a = fields.Float(readonly=True)
    sweden_blackbox_tax_category_b = fields.Float(readonly=True)
    sweden_blackbox_tax_category_c = fields.Float(readonly=True)
    sweden_blackbox_tax_category_d = fields.Float(readonly=True)
    sweden_blackbox_device = fields.Many2one(
        related="session_id.config_id.iface_sweden_fiscal_data_module", readonly=True
    )
    is_reprint = fields.Boolean(readonly=True)

    @api.ondelete(at_uninstall=True)
    def _unlink_except_registered_order(self):
        for order in self:
            if order.config_id.iface_sweden_fiscal_data_module:
                raise UserError(_("Deleting of registered orders is not allowed."))

    def set_is_reprint(self):
        """No longer used, remove in master"""
        return True

    def is_already_reprint(self):
        """No longer used, remove in master"""
        return True
