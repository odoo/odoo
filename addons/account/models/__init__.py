# -*- coding: utf-8 -*-

from . import sequence_mixin
from . import partner
from . import res_partner_bank
from . import account_account_tag
from . import account_account
from . import account_journal
from . import account_tax
from . import account_tax_carryover_line
from . import account_tax_report
from . import account_reconcile_model
from . import account_payment_term
from . import account_move
from . import account_move_line_tax_details
from . import account_analytic_default
from . import account_partial_reconcile
from . import account_full_reconcile
from . import account_payment
from . import account_payment_method
from . import account_bank_statement
from . import chart_template
from . import account_analytic_line
from . import account_journal_dashboard
from . import product
from . import company
from . import res_config_settings
from . import account_cash_rounding
from . import account_incoterms
from . import digest
from . import res_users
from . import ir_actions_report
from . import res_currency
from . import res_bank
from . import mail_thread


DEFAULT_CHART_TEMPLATE = 'generic_coa'

def templ(code, name, country=None, modules=None, parent=None):
    return (code, {
        'name': name,
        'country': country or f"base.{code[:2]}" if code != DEFAULT_CHART_TEMPLATE else None,
        'modules': modules or [f'l10n_{code[:2]}'],
        'parent': parent,
    })


CHART_TEMPLATES = dict([
    templ(DEFAULT_CHART_TEMPLATE, 'Generic Chart Template', None, ['account']),
    templ('be', 'BE Belgian PCMN'),
    templ('it', 'Italy - Generic Chart of Accounts'),
    templ('fr', 'Plan Comptable Général (France)'),
    templ('ch', 'Plan comptable 2015 (Suisse)'),
    templ('de_skr03', 'Deutscher Kontenplan SKR03', modules=['l10n_de', 'l10n_de_skr03']),
    templ('de_skr04', 'Deutscher Kontenplan SKR04', modules=['l10n_de', 'l10n_de_skr04']),
    templ('ae', 'U.A.E Chart of Accounts - Standard'),
    templ('se', 'Swedish BAS Chart of Account Minimalist'),
    templ('se_k2', 'Swedish BAS Chart of Account complete K2', parent='se'),
    templ('se_k3', 'Swedish BAS Chart of Account complete K3', parent='se_k2'),
])
