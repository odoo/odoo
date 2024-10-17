# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

def _set_fiscal_country(env):
    """ Sets the fiscal country on existing companies when installing the module.
    That field is an editable computed field. It doesn't automatically get computed
    on existing records by the ORM when installing the module, so doing that by hand
    ensures existing records will get a value for it if needed.
    """
    env['res.company'].search([]).compute_account_tax_fiscal_country()


def _account_post_init(env):
    _set_fiscal_country(env)

# imported here to avoid dependency cycle issues
# pylint: disable=wrong-import-position
from . import controllers
from . import models
from . import demo
from . import wizard
from . import report
from . import tools

from .demo.account_demo import AccountChartTemplate
from .models.account_account import AccountAccount, AccountGroup
from .models.account_account_tag import AccountAccountTag
from .models.account_analytic_account import AccountAnalyticAccount
from .models.account_analytic_distribution_model import AccountAnalyticDistributionModel
from .models.account_analytic_line import AccountAnalyticLine
from .models.account_analytic_plan import AccountAnalyticApplicability
from .models.account_bank_statement import AccountBankStatement
from .models.account_bank_statement_line import AccountBankStatementLine, AccountMove
from .models.account_cash_rounding import AccountCashRounding
from .models.account_code_mapping import AccountCodeMapping
from .models.account_full_reconcile import AccountFullReconcile
from .models.account_incoterms import AccountIncoterms
from .models.account_journal import AccountJournalGroup
from .models.account_journal_dashboard import AccountJournal
from .models.account_lock_exception import AccountLock_Exception
from .models.account_move_line_tax_details import AccountMoveLine
from .models.account_move_send import AccountMoveSend
from .models.account_partial_reconcile import AccountPartialReconcile
from .models.account_payment import AccountPayment
from .models.account_payment_method import AccountPaymentMethod, AccountPaymentMethodLine
from .models.account_payment_term import AccountPaymentTerm, AccountPaymentTermLine
from .models.account_reconcile_model import (
    AccountReconcileModel, AccountReconcileModelLine,
    AccountReconcileModelPartnerMapping,
)
from .models.account_report import (
    AccountReport, AccountReportColumn, AccountReportExpression,
    AccountReportExternalValue, AccountReportLine,
)
from .models.account_root import AccountRoot
from .models.account_tax import AccountTax, AccountTaxGroup, AccountTaxRepartitionLine
from .models.company import ResCompany
from .models.decimal_precision import DecimalPrecision
from .models.digest import DigestDigest
from .models.ir_actions_report import IrActionsReport
from .models.ir_attachment import IrAttachment
from .models.ir_module import IrModuleModule
from .models.ir_ui_menu import IrUiMenu
from .models.mail_message import MailMessage
from .models.mail_template import MailTemplate
from .models.mail_tracking_value import MailTrackingValue
from .models.merge_partner_automatic import BasePartnerMergeAutomaticWizard
from .models.onboarding_onboarding_step import OnboardingOnboardingStep
from .models.partner import (
    AccountFiscalPosition, AccountFiscalPositionAccount,
    AccountFiscalPositionTax, ResPartner,
)
from .models.product import ProductCategory, ProductProduct, ProductTemplate
from .models.res_config_settings import ResConfigSettings
from .models.res_currency import ResCurrency
from .models.res_partner_bank import ResPartnerBank
from .models.res_users import ResGroups
from .models.sequence_mixin import SequenceMixin
from .models.uom_uom import UomUom
from .report.account_hash_integrity_templates import ReportAccountReport_Hash_Integrity
from .report.account_invoice_report import (
    AccountInvoiceReport, ReportAccountReport_Invoice,
    ReportAccountReport_Invoice_With_Payments,
)
from .wizard.account_automatic_entry_wizard import AccountAutomaticEntryWizard
from .wizard.account_autopost_bills_wizard import AccountAutopostBillsWizard
from .wizard.account_merge_wizard import AccountMergeWizard, AccountMergeWizardLine
from .wizard.account_move_reversal import AccountMoveReversal
from .wizard.account_move_send_batch_wizard import AccountMoveSendBatchWizard
from .wizard.account_move_send_wizard import AccountMoveSendWizard
from .wizard.account_payment_register import AccountPaymentRegister
from .wizard.account_resequence import AccountResequenceWizard
from .wizard.account_secure_entries_wizard import AccountSecureEntriesWizard
from .wizard.account_validate_account_move import ValidateAccountMove
from .wizard.accrued_orders import AccountAccruedOrdersWizard
from .wizard.base_document_layout import BaseDocumentLayout
from .wizard.setup_wizards import AccountFinancialYearOp, AccountSetupBankManualConfig
