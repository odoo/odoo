# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from .models import (
    BarcodeRule, IrActionsReport, ProcurementGroup, ProductCategory,
    ProductPackaging, ProductProduct, ProductRemoval, ProductTemplate, ResCompany,
    ResConfigSettings, ResPartner, ResUsers, StockLocation, StockLot, StockMove, StockMoveLine,
    StockPackageType, StockPackage_Level, StockPicking, StockPickingType, StockPutawayRule,
    StockQuant, StockQuantPackage, StockReplenishMixin, StockRoute, StockRule, StockScrap,
    StockScrapReasonTag, StockStorageCategory, StockStorageCategoryCapacity, StockWarehouse,
    StockWarehouseOrderpoint, UomUom,
)
from .report import (
    ReportStockLabel_Lot_Template_View, ReportStockLabel_Product_Product_View,
    ReportStockQuantity, ReportStockReport_Reception, ReportStockReport_Stock_Rule,
    StockForecasted_Product_Product, StockForecasted_Product_Template, StockLotReport,
    StockTraceabilityReport,
)
from .wizard import (
    LotLabelLayout, PickingLabelType, ProductLabelLayout, ProductReplenish,
    StockBackorderConfirmation, StockBackorderConfirmationLine, StockChangeProductQty,
    StockInventoryAdjustmentName, StockInventoryConflict, StockInventoryWarning,
    StockOrderpointSnooze, StockPackageDestination, StockQuantRelocate, StockQuantityHistory,
    StockReplenishmentInfo, StockReplenishmentOption, StockRequestCount, StockReturnPicking,
    StockReturnPickingLine, StockRulesReport, StockTrackConfirmation, StockTrackLine,
    StockWarnInsufficientQty, StockWarnInsufficientQtyScrap,
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
