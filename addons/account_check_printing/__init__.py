# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import models
from . import wizard

from .models.account_journal import AccountJournal
from .models.account_payment import AccountPayment
from .models.account_payment_method import AccountPaymentMethod
from .models.res_company import ResCompany
from .models.res_config_settings import ResConfigSettings
from .wizard.print_prenumbered_checks import PrintPrenumberedChecks


def create_check_sequence_on_bank_journals(env):
    env['account.journal'].search([('type', '=', 'bank')])._create_check_sequence()
