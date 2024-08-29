# -*- coding: utf-8 -*-
from odoo.addons import account

from odoo import fields, models


class AccountMove(models.Model, account.AccountMove):

    l10n_sg_permit_number = fields.Char(string="Permit No.")

    l10n_sg_permit_number_date = fields.Date(string="Date of permit number")
