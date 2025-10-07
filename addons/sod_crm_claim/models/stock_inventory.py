# Copyright 2019-2023 Sodexis
# License OPL-1 (See LICENSE file for full copyright and licensing details)

from odoo import api, fields, models


class StockQuant(models.Model):
    _inherit = "stock.quant"

    claim_id = fields.Many2one("crm.claim", string="Return")

    @api.model
    def _get_inventory_fields_write(self):
        """Returns a list of fields user can edit when he/she want to edit a quant in
        `inventory_mode`, [ADD] claim_id for Allowed fields inclusion.
        """
        fields = super()._get_inventory_fields_write()
        fields.append("claim_id")
        return fields
