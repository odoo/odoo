# coding: utf-8
from odoo import fields, models
from odoo.addons import account, base_vat


class ResCompany(base_vat.ResCompany, account.ResCompany):

    l10n_no_bronnoysund_number = fields.Char(related='partner_id.l10n_no_bronnoysund_number', readonly=False)
