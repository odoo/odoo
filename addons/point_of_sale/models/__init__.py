# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .account_bank_statement import AccountBankStatementLine
from .pos_load_mixin import PosLoadMixin
from .account_payment import AccountPayment
from .account_journal import AccountJournal
from .account_tax import AccountTax
from .account_tax_group import AccountTaxGroup
from .account_move import AccountMoveLine, AccountMove
from .pos_bus_mixin import PosBusMixin
from .barcode_rule import BarcodeRule
from . import binary
from .digest import DigestDigest
from .ir_binary import IrBinary
from .pos_category import PosCategory
from .pos_config import PosConfig
from .pos_order import PosPackOperationLot, PosOrderLine, AccountCashRounding, PosOrder
from .pos_session import ProcurementGroup, PosSession
from .product import ProductTemplateAttributeValue, ProductProduct, ProductTemplateAttributeLine, ProductTemplate, ProductCategory, ProductAttributeCustomValue, UomCategory, UomUom, ProductPricelist, ProductPricelistItem, ProductAttribute, ProductPackaging
from .product_combo import ProductCombo
from .product_combo_item import ProductComboItem
from .res_partner import ResPartner
from .res_company import ResCompany
from .res_config_settings import ResConfigSettings
from .stock_picking import ProcurementGroup, StockPickingType, StockMove, StockPicking
from .stock_rule import StockRule
from .stock_warehouse import StockWarehouse
from .pos_payment import PosPayment
from .pos_payment_method import PosPaymentMethod
from .pos_bill import PosBill
from .report_sale_details import ReportPointOfSaleReportSaledetails
from .pos_printer import PosPrinter
from .pos_note import PosNote
from .res_users import ResUsers
from .decimal_precision import DecimalPrecision
from .res_country import ResCountry
from .res_country_state import ResCountryState
from .res_lang import ResLang
from .account_fiscal_position import AccountFiscalPosition
from .account_fiscal_position_tax import AccountFiscalPositionTax
from .res_currency import ResCurrency
from .ir_ui_view import IrUiView
from .mail_compose_message import MailComposeMessage
