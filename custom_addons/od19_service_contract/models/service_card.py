# -*- coding: utf-8 -*-
from odoo import fields, models


class ServiceCard(models.Model):
    _inherit = "od19.service.card"

    contract_id = fields.Many2one(
        comodel_name="contract.contract",
        string="Service Contract",
        ondelete="set null",
        index=True,
        help="Service contract this preventive-maintenance card belongs to.",
    )
