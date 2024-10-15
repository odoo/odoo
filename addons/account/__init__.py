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
from .models import (
    AccountAccount, AccountAccountTag, AccountAnalyticAccount,
    AccountAnalyticApplicability, AccountAnalyticDistributionModel, AccountAnalyticLine,
    AccountBankStatement, AccountBankStatementLine, AccountCashRounding, AccountChartTemplate,
    AccountCodeMapping, AccountFiscalPosition, AccountFiscalPositionAccount,
    AccountFiscalPositionTax, AccountFullReconcile, AccountGroup, AccountIncoterms,
    AccountJournal, AccountJournalGroup, AccountLock_Exception, AccountMove, AccountMoveLine,
    AccountMoveSend, AccountPartialReconcile, AccountPayment, AccountPaymentMethod,
    AccountPaymentMethodLine, AccountPaymentTerm, AccountPaymentTermLine, AccountReconcileModel,
    AccountReconcileModelLine, AccountReconcileModelPartnerMapping, AccountReport,
    AccountReportColumn, AccountReportExpression, AccountReportExternalValue, AccountReportLine,
    AccountRoot, AccountTax, AccountTaxGroup, AccountTaxRepartitionLine, DecimalPrecision,
    DigestDigest, IrActionsReport, IrAttachment, IrModuleModule, IrUiMenu, MailMessage,
    MailTemplate, MailTrackingValue, OnboardingOnboardingStep, ProductCategory, ProductProduct,
    ProductTemplate, ResCompany, ResConfigSettings, ResCurrency, ResGroups, ResPartner,
    ResPartnerBank, SequenceMixin, UomUom,
)
from . import demo
from .wizard import (
    AccountAccruedOrdersWizard, AccountAutomaticEntryWizard,
    AccountAutopostBillsWizard, AccountFinancialYearOp, AccountMergeWizard,
    AccountMergeWizardLine, AccountMoveReversal, AccountMoveSendBatchWizard,
    AccountMoveSendWizard, AccountPaymentRegister, AccountResequenceWizard,
    AccountSecureEntriesWizard, AccountSetupBankManualConfig, BaseDocumentLayout,
    BasePartnerMergeAutomaticWizard, ValidateAccountMove,
)
from .report import (
    AccountInvoiceReport, ReportAccountReport_Hash_Integrity,
    ReportAccountReport_Invoice, ReportAccountReport_Invoice_With_Payments,
)
from . import tools
