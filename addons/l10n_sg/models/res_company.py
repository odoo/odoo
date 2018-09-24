# -*- coding: utf-8 -*-

from odoo import fields, models

class ResCompany(models.Model):
    _name = 'res.company'
    _description = 'Companies'
    _inherit = 'res.company'

    l10n_sg_unique_entity_number = fields.Char(string='UEN', related="partner_id.l10n_sg_unique_entity_number", readonly=False)
