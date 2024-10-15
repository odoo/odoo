# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from odoo.addons import account


class AccountMove(account.AccountMove):

    l10n_rs_turnover_date = fields.Date(string='Turnover Date')
