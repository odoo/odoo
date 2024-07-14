# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sepa_orgid_id = fields.Char(related='company_id.sepa_orgid_id', string="Identification", readonly=False,
        help="Identification assigned by an institution (eg. VAT number).")
    sepa_orgid_issr = fields.Char(related='company_id.sepa_orgid_issr', string="Issuer", readonly=False,
        help="Will appear in SEPA payments as the name of the party initiating the payment. Limited to 70 characters.")
    sepa_initiating_party_name = fields.Char(related='company_id.sepa_initiating_party_name', string="Your Company Name", help="Name of the Creditor Reference Party. Usage Rule: Limited to 70 characters in length.", readonly=False)
