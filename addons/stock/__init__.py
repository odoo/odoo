# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report
from . import wizard

from .models.barcode import BarcodeRule
from .models.ir_actions_report import IrActionsReport
from .models.product import (
    ProductCategory, ProductPackaging, ProductProduct, ProductTemplate,
    UomUom,
)
from .models.product_strategy import ProductRemoval, StockPutawayRule
from .models.res_company import ResCompany
from .models.res_config_settings import ResConfigSettings
from .models.res_partner import ResPartner
from .models.res_users import ResUsers
from .models.stock_location import StockLocation, StockRoute
from .models.stock_lot import StockLot
from .models.stock_move import StockMove
from .models.stock_move_line import StockMoveLine
from .models.stock_orderpoint import StockWarehouseOrderpoint
from .models.stock_package_level import StockPackage_Level
from .models.stock_package_type import StockPackageType
from .models.stock_picking import StockPicking, StockPickingType
from .models.stock_quant import StockQuant, StockQuantPackage
from .models.stock_replenish_mixin import StockReplenishMixin
from .models.stock_rule import ProcurementGroup, StockRule
from .models.stock_scrap import StockScrap, StockScrapReasonTag
from .models.stock_storage_category import StockStorageCategory, StockStorageCategoryCapacity
from .models.stock_warehouse import StockWarehouse
from .report.product_label_report import (
    ReportStockLabel_Lot_Template_View,
    ReportStockLabel_Product_Product_View,
)
from .report.report_stock_quantity import ReportStockQuantity
from .report.report_stock_reception import ReportStockReport_Reception
from .report.report_stock_rule import ReportStockReport_Stock_Rule
from .report.stock_forecasted import (
    StockForecasted_Product_Product,
    StockForecasted_Product_Template,
)
from .report.stock_lot_customer import StockLotReport
from .report.stock_traceability import StockTraceabilityReport
from .wizard.product_label_layout import ProductLabelLayout
from .wizard.product_replenish import ProductReplenish
from .wizard.stock_backorder_confirmation import (
    StockBackorderConfirmation,
    StockBackorderConfirmationLine,
)
from .wizard.stock_change_product_qty import StockChangeProductQty
from .wizard.stock_inventory_adjustment_name import StockInventoryAdjustmentName
from .wizard.stock_inventory_conflict import StockInventoryConflict
from .wizard.stock_inventory_warning import StockInventoryWarning
from .wizard.stock_label_type import PickingLabelType
from .wizard.stock_lot_label_layout import LotLabelLayout
from .wizard.stock_orderpoint_snooze import StockOrderpointSnooze
from .wizard.stock_package_destination import StockPackageDestination
from .wizard.stock_picking_return import StockReturnPicking, StockReturnPickingLine
from .wizard.stock_quant_relocate import StockQuantRelocate
from .wizard.stock_quantity_history import StockQuantityHistory
from .wizard.stock_replenishment_info import StockReplenishmentInfo, StockReplenishmentOption
from .wizard.stock_request_count import StockRequestCount
from .wizard.stock_rules_report import StockRulesReport
from .wizard.stock_track_confirmation import StockTrackConfirmation, StockTrackLine
from .wizard.stock_warn_insufficient_qty import (
    StockWarnInsufficientQty,
    StockWarnInsufficientQtyScrap,
)


# TODO: Apply proper fix & remove in master
def pre_init_hook(env):
    env['ir.model.data'].search([
        ('model', 'like', 'stock'),
        ('module', '=', 'stock')
    ]).unlink()

def _assign_default_mail_template_picking_id(env):
    company_ids_without_default_mail_template_id = env['res.company'].search([
        ('stock_mail_confirmation_template_id', '=', False)
    ])
    default_mail_template_id = env.ref('stock.mail_template_data_delivery_confirmation', raise_if_not_found=False)
    if default_mail_template_id:
        company_ids_without_default_mail_template_id.write({
            'stock_mail_confirmation_template_id': default_mail_template_id.id,
        })

def uninstall_hook(env):
    picking_type_ids = env["stock.picking.type"].with_context({"active_test": False}).search([])
    picking_type_ids.sequence_id.unlink()
