# coding: utf-8
from odoo.addons import base
from odoo import fields, models


class ResCompany(models.Model, base.ResCompany):

    l10n_no_bronnoysund_number = fields.Char(related='partner_id.l10n_no_bronnoysund_number', readonly=False)
