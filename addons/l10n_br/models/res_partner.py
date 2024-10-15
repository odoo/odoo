# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models
from odoo.addons import account, l10n_latam_base, base_address_extended


class ResPartner(account.ResPartner, base_address_extended.ResPartner, l10n_latam_base.ResPartner):

    l10n_br_ie_code = fields.Char(string="IE", help="State Tax Identification Number. Should contain 9-14 digits.")
    l10n_br_im_code = fields.Char(string="IM", help="Municipal Tax Identification Number")
    l10n_br_isuf_code = fields.Char(string="SUFRAMA code", help="SUFRAMA registration number.")
