# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _
from odoo.exceptions import UserError


class BankStatement(models.Model):
    _inherit = 'account.bank.statement'

    def button_draft(self):
        self.state = 'open'


