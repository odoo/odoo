# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .product_label_layout import ProductLabelLayout
from .stock_picking_return import StockReturnPicking, StockReturnPickingLine
from .stock_change_product_qty import StockChangeProductQty
from .stock_inventory_conflict import StockInventoryConflict
from .stock_inventory_warning import StockInventoryWarning
from .stock_inventory_adjustment_name import StockInventoryAdjustmentName
from .stock_label_type import PickingLabelType
from .stock_lot_label_layout import LotLabelLayout
from .stock_backorder_confirmation import (
    StockBackorderConfirmation,
    StockBackorderConfirmationLine,
)
from .stock_quantity_history import StockQuantityHistory
from .stock_rules_report import StockRulesReport
from .stock_warn_insufficient_qty import StockWarnInsufficientQty, StockWarnInsufficientQtyScrap
from .product_replenish import ProductReplenish
from .stock_track_confirmation import StockTrackConfirmation, StockTrackLine
from .stock_package_destination import StockPackageDestination
from .stock_orderpoint_snooze import StockOrderpointSnooze
from .stock_request_count import StockRequestCount
from .stock_replenishment_info import StockReplenishmentInfo, StockReplenishmentOption
from .stock_quant_relocate import StockQuantRelocate
