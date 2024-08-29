# -*- coding: utf-8 -*-
from odoo.addons import account
from odoo import fields, models


class AccountMove(models.Model, account.AccountMove):

    buyer_reference = fields.Char(help="'Service Exécutant' in Chorus PRO.")
    contract_reference = fields.Char(help="'Numéro de Marché' in Chorus PRO.")
    purchase_order_reference = fields.Char(help="'Engagement Juridique' in Chorus PRO.")
