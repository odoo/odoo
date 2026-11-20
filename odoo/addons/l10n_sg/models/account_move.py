# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_sg_permit_number = fields.Char(string="Permit No.")

    l10n_sg_permit_number_date = fields.Date(string="Date of permit number")
