# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .models import (
    AccountBankStatementLine, AccountCashRounding, AccountFiscalPosition,
    AccountFiscalPositionTax, AccountJournal, AccountMove, AccountMoveLine, AccountPayment,
    AccountTax, AccountTaxGroup, BarcodeRule, DecimalPrecision, DigestDigest, IrBinary, IrUiView,
    MailComposeMessage, PosBill, PosBusMixin, PosCategory, PosConfig, PosLoadMixin, PosNote,
    PosOrder, PosOrderLine, PosPackOperationLot, PosPayment, PosPaymentMethod, PosPrinter,
    PosSession, ProcurementGroup, ProductAttribute, ProductAttributeCustomValue, ProductCategory,
    ProductCombo, ProductComboItem, ProductPackaging, ProductPricelist, ProductPricelistItem,
    ProductProduct, ProductTemplate, ProductTemplateAttributeLine, ProductTemplateAttributeValue,
    ReportPoint_Of_SaleReport_Saledetails, ResCompany, ResConfigSettings, ResCountry,
    ResCountryState, ResCurrency, ResLang, ResPartner, ResUsers, StockMove, StockPicking,
    StockPickingType, StockRule, StockWarehouse, UomCategory, UomUom,
)
from . import controllers
from .report import ReportPoint_Of_SaleReport_Invoice, ReportPosOrder
from .wizard import (
    PosCloseSessionWizard, PosDailySalesReportsWizard, PosDetailsWizard,
    PosMakePayment,
)


def uninstall_hook(env):
    #The search domain is based on how the sequence is defined in the _get_sequence_values method in /addons/point_of_sale/models/stock_warehouse.py
    env['ir.sequence'].search([('name', 'ilike', '%Picking POS%'), ('prefix', 'ilike', '%/POS/%')]).unlink()
