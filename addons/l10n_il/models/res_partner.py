# -*- coding: utf-8 -*-

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_il_self_invoice = fields.Boolean(string='Self Invoice', help="Set this to true to when self invoice needs to be created")
