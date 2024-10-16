# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .models import (
    AccountChartTemplate, AccountFiscalPosition, AccountJournal, AccountMove,
    AccountMoveLine, AccountTaxGroup, L10n_ArAfipResponsibilityType, L10n_LatamDocumentType,
    L10n_LatamIdentificationType, ResCompany, ResCountry, ResCurrency, ResPartner, ResPartnerBank,
    UomUom,
)
from .report import AccountInvoiceReport
from . import demo
