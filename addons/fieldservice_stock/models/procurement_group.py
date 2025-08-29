# Copyright (C) 2018 Brian McMaster
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ProcurementGroup(models.Model):
    _inherit = "procurement.group"

    fsm_order_id = fields.Many2one("fsm.order", "Field Service Order")
