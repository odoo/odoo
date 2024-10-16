# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.addons import account, l10n_fr_account, account_edi_ubl_cii


class AccountMove(account.AccountMove, account_edi_ubl_cii.AccountMove, l10n_fr_account.AccountMove):

    buyer_reference = fields.Char(help="'Service Exécutant' in Chorus PRO.")
    contract_reference = fields.Char(help="'Numéro de Marché' in Chorus PRO.")
    purchase_order_reference = fields.Char(help="'Engagement Juridique' in Chorus PRO.")
