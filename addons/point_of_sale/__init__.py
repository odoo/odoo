# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import controllers
from . import report
from . import wizard

from .models.account_bank_statement import AccountBankStatementLine
from .models.account_fiscal_position import AccountFiscalPosition
from .models.account_fiscal_position_tax import AccountFiscalPositionTax
from .models.account_journal import AccountJournal
from .models.account_move import AccountMove, AccountMoveLine
from .models.account_payment import AccountPayment
from .models.account_tax import AccountTax
from .models.account_tax_group import AccountTaxGroup
from .models.barcode_rule import BarcodeRule
from .models.decimal_precision import DecimalPrecision
from .models.digest import DigestDigest
from .models.ir_binary import IrBinary
from .models.ir_ui_view import IrUiView
from .models.mail_compose_message import MailComposeMessage
from .models.pos_bill import PosBill
from .models.pos_bus_mixin import PosBusMixin
from .models.pos_category import PosCategory
from .models.pos_config import PosConfig
from .models.pos_load_mixin import PosLoadMixin
from .models.pos_note import PosNote
from .models.pos_order import AccountCashRounding, PosOrder, PosOrderLine, PosPackOperationLot
from .models.pos_payment import PosPayment
from .models.pos_payment_method import PosPaymentMethod
from .models.pos_printer import PosPrinter
from .models.pos_session import PosSession, ProcurementGroup
from .models.product import (
    ProductAttribute, ProductAttributeCustomValue, ProductCategory,
    ProductPackaging, ProductPricelist, ProductPricelistItem, ProductProduct, ProductTemplate,
    ProductTemplateAttributeLine, ProductTemplateAttributeValue, UomCategory, UomUom,
)
from .models.product_combo import ProductCombo
from .models.product_combo_item import ProductComboItem
from .models.report_sale_details import ReportPoint_Of_SaleReport_Saledetails
from .models.res_company import ResCompany
from .models.res_config_settings import ResConfigSettings
from .models.res_country import ResCountry
from .models.res_country_state import ResCountryState
from .models.res_currency import ResCurrency
from .models.res_lang import ResLang
from .models.res_partner import ResPartner
from .models.res_users import ResUsers
from .models.stock_picking import StockMove, StockPicking, StockPickingType
from .models.stock_rule import StockRule
from .models.stock_warehouse import StockWarehouse
from .report.pos_invoice import ReportPoint_Of_SaleReport_Invoice
from .report.pos_order_report import ReportPosOrder
from .wizard.pos_close_session_wizard import PosCloseSessionWizard
from .wizard.pos_daily_sales_reports import PosDailySalesReportsWizard
from .wizard.pos_details import PosDetailsWizard
from .wizard.pos_payment import PosMakePayment


def uninstall_hook(env):
    #The search domain is based on how the sequence is defined in the _get_sequence_values method in /addons/point_of_sale/models/stock_warehouse.py
    env['ir.sequence'].search([('name', 'ilike', '%Picking POS%'), ('prefix', 'ilike', '%/POS/%')]).unlink()
