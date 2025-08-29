# Copyright (C) 2018 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class FSMWizard(models.TransientModel):
    _inherit = "fsm.wizard"

    def _prepare_fsm_location(self, partner):
        res = super()._prepare_fsm_location(partner)
        res["inventory_location_id"] = partner.property_stock_customer.id
        return res
