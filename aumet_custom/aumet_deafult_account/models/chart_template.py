# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = "res.partner"

    property_account_payable_id = fields.Many2one('account.account', company_dependent=True,
        string="Account Payable",
        domain="[('internal_type', '=', 'payable'), ('deprecated', '=', False), ('company_id', '=', current_company_id)]",
        help="This account will be used instead of the default one as the payable account for the current partner",
        required=True,default=37)
    property_account_receivable_id = fields.Many2one('account.account', company_dependent=True,
        string="Account Receivable",
        domain="[('internal_type', '=', 'receivable'), ('deprecated', '=', False), ('company_id', '=', current_company_id)]",
        help="This account will be used instead of the default one as the receivable account for the current partner",
        required=True,default=32)
