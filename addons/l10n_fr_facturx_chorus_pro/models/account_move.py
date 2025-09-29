# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    buyer_reference = fields.Char(help="'Code de Service' in Chorus PRO.")
    contract_reference = fields.Char(help="'Numéro de Marché' in Chorus PRO.")
    purchase_order_reference = fields.Char(help="'Engagement Juridique' in Chorus PRO.")
