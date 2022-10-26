# coding: utf-8
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_no_bronnoysund_number = fields.Char(string='Register of Legal Entities (Brønnøysund Register Center)', size=9)
