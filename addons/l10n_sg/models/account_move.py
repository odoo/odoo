# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo.addons import account


class AccountMove(account.AccountMove):

    l10n_sg_permit_number = fields.Char(string="Permit No.")

    l10n_sg_permit_number_date = fields.Date(string="Date of permit number")
