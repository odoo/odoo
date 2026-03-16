# Purchase & Inventory Modules — Detailed Feature Analysis

## Purpose

This document provides a comprehensive analysis of Odoo's **Purchase** and **Inventory (Stock)** modules,
their features, functionalities, dependencies, and interconnections. The goal is to identify what is needed
to use these modules as **standalone** components with reduced code weight and optimized performance.

---

## Table of Contents

1. [Module Overview & Code Metrics](#1-module-overview--code-metrics)
2. [Purchase Module — Detailed Features](#2-purchase-module--detailed-features)
3. [Inventory (Stock) Module — Detailed Features](#3-inventory-stock-module--detailed-features)
4. [Purchase-Stock Bridge Module](#4-purchase-stock-bridge-module)
5. [Stock-Account Bridge Module](#5-stock-account-bridge-module)
6. [Full Dependency Tree](#6-full-dependency-tree)
7. [Feature Classification for Standalone Usage](#7-feature-classification-for-standalone-usage)
8. [Optimization Recommendations](#8-optimization-recommendations)

---

## 1. Module Overview & Code Metrics

### Code Size Summary

| Module            | Model Files | Total Source Files | Lines of Code (py+xml+js) |
|-------------------|-------------|-------------------|---------------------------|
| `stock`           | 24          | 216               | ~55,778                   |
| `purchase`        | 13          | 80                | ~11,285                   |
| `stock_account`   | 16          | 55                | ~12,305                   |
| `purchase_stock`  | 14          | 78                | ~17,000                   |
| **TOTAL**         | **67**      | **429**           | **~96,368**               |

### Largest Model Files (Lines of Code)

| File                          | LOC   | Complexity Level |
|-------------------------------|-------|------------------|
| `stock/models/stock_move.py`      | 2,638 | Very High        |
| `stock/models/stock_picking.py`   | 2,084 | Very High        |
| `stock/models/stock_quant.py`     | 1,696 | High             |
| `purchase/models/purchase_order.py` | 1,373 | High           |
| `stock/models/product.py`         | 1,315 | High             |
| `stock/models/stock_warehouse.py` | 1,163 | High             |
| `stock/models/stock_move_line.py` | 1,139 | High             |
| `stock/models/stock_rule.py`      | 752   | Medium           |
| `stock/models/stock_orderpoint.py`| 724   | Medium           |
| `purchase/models/purchase_order_line.py` | 618 | Medium     |
| `stock/models/stock_location.py`  | 587   | Medium           |

---

## 2. Purchase Module — Detailed Features

**Path**: `addons/purchase/`
**Manifest Dependencies**: `account` only
**Application**: Yes (top-level module)

### 2.1 Core Models

#### 2.1.1 Purchase Order (`purchase.order` — 1,373 LOC)

**Inherits**: `portal.mixin`, `product.catalog.mixin`, `mail.thread`, `mail.activity.mixin`

**State Machine**:
```
Draft → RFQ Sent → To Approve (optional 2-step) → Purchase Order → Done/Cancel
```

**Key Fields**:
| Field | Type | Purpose |
|-------|------|---------|
| `name` | Char | Order reference (auto-sequence) |
| `state` | Selection | draft/sent/to approve/purchase/cancel |
| `partner_id` | Many2one | Vendor |
| `order_line` | One2many | Purchase order lines |
| `date_order` | Datetime | Order deadline |
| `date_approve` | Datetime | Confirmation date |
| `amount_untaxed/tax/total` | Monetary | Computed totals |
| `currency_id` | Many2one | Currency (from vendor or company) |
| `fiscal_position_id` | Many2one | Tax mapping |
| `payment_term_id` | Many2one | Payment terms |
| `invoice_status` | Selection | no/to invoice/invoiced |
| `invoice_ids` | Many2many | Related vendor bills |
| `user_id` | Many2one | Buyer (purchase representative) |
| `dest_address_id` | Many2one | Drop-ship address |
| `priority` | Selection | Normal/Urgent |
| `locked` | Boolean | Prevents editing confirmed POs |

**Core Features**:

1. **Order Lifecycle Management**
   - `button_confirm()` — Confirms draft/sent orders
   - `button_approve()` — Approves orders (2-step workflow)
   - `button_cancel()` — Cancels with validation
   - `button_draft()` — Resets to draft
   - `button_lock()/button_unlock()` — Lock/unlock editing

2. **Two-Step Approval Workflow**
   - `_approval_allowed()` — Checks if user can approve based on amount thresholds
   - Configurable via `po_double_validation` and `po_double_validation_amount` on company

3. **Tax & Amount Calculation**
   - `_amount_all()` — Computes all amounts including taxes
   - `_compute_tax_totals()` — Prepares tax summary for UI
   - `_compute_currency_rate()` — Exchange rate calculation

4. **Invoice (Vendor Bill) Management**
   - `action_create_invoice()` — Creates vendor bill from PO
   - `_prepare_invoice()` — Prepares invoice values
   - `_get_invoiced()` — Computes invoice_status
   - Down-payment support via `_create_downpayments()`

5. **Vendor Auto-Registration**
   - `_add_supplier_to_product()` — Auto-registers supplier on product when PO confirmed
   - `_prepare_supplier_info()` — Prepares supplierinfo data

6. **Communication & Portal**
   - `action_rfq_send()` — Opens email composer for RFQ/PO
   - `action_acknowledge()` — Marks as acknowledged by vendor
   - Portal routes for vendor self-service (view, update dates, download EDI)

7. **RFQ Merging**
   - `action_merge()` — Merges multiple RFQs into one
   - `_fetch_duplicate_orders()` — Detects duplicate orders

8. **Receipt Reminders**
   - `_send_reminder_mail()` — Auto-sends receipt reminders
   - Daily cron job checks and sends

9. **Product Catalog Integration**
   - `action_add_from_catalog()` — Opens product catalog browser
   - `_get_product_price_and_data()` — Gets vendor pricing in real-time

10. **Dashboard**
    - `retrieve_dashboard()` — Returns draft counts, sent counts, late orders, etc.

11. **EDI Support**
    - `_get_edi_builders()` — Extensible EDI export
    - Download EDI XML from portal

#### 2.1.2 Purchase Order Line (`purchase.order.line` — 618 LOC)

**Inherits**: `analytic.mixin`

**Key Fields**:
| Field | Type | Purpose |
|-------|------|---------|
| `product_id` | Many2one | Product |
| `product_qty` | Float | Ordered quantity |
| `price_unit` | Float | Unit price (computed from seller) |
| `discount` | Float | Percentage discount |
| `date_planned` | Datetime | Expected arrival |
| `tax_ids` | Many2many | Applicable taxes |
| `qty_invoiced` | Float | Invoiced quantity (computed) |
| `qty_received` | Float | Received quantity (computed/manual) |
| `qty_to_invoice` | Float | Remaining to invoice |
| `selected_seller_id` | Many2one | Best supplier match |
| `is_downpayment` | Boolean | Down-payment line |

**Core Features**:

1. **Dynamic Pricing** — Computes price, date, and description from vendor pricelist
2. **Tax Computation** — Auto-applies taxes from fiscal position
3. **Quantity Tracking** — Tracks ordered vs received vs invoiced
4. **Analytic Distribution** — Cost center/project allocation
5. **Invoice Preparation** — `_prepare_account_move_line()` for bill creation
6. **Minimum Qty Suggestion** — From vendor pricelist minimums
7. **Product Warnings** — Displays warnings on product selection

#### 2.1.3 Purchase Bill Line Match (`purchase.bill.line.match` — 206 LOC)

**Virtual model** (SQL union view) for matching PO lines with vendor bill lines.

**Features**:
- Union of un-invoiced PO lines and unlinked bill lines
- `action_match_lines()` — Creates/matches invoices from selections
- `_action_create_bill_from_po_lines()` — Creates bill from PO lines
- `action_add_to_po()` — Adds bill lines to existing PO

#### 2.1.4 Account Move Extensions (`account_invoice.py` — 559 LOC)

**Extends**: `account.move` and `account.move.line`

**Key Features**:
1. **Intelligent PO Matching Algorithm**:
   - Total amount match (2% tolerance)
   - Subset matching (0-1 knapsack algorithm)
   - Individual line matching by price/qty/name similarity
   - Vendor + total fallback

2. **Auto-completion** — Load PO data into vendor bill
3. **Purchase Warning Text** — Aggregated warnings for vendor/products

### 2.2 Configuration Models

| Model | Key Fields | Purpose |
|-------|-----------|---------|
| `res.company` | `po_lead`, `po_lock`, `po_double_validation`, `po_double_validation_amount` | Purchase lead time, lock policy, approval settings |
| `res.partner` | `property_purchase_currency_id`, `receipt_reminder_email`, `reminder_date_before_receipt`, `buyer_id` | Vendor purchase preferences |
| `product.template` | `purchase_method` (purchase/receive) | Control when qty is considered received |

### 2.3 Reports

| Report | Purpose |
|--------|---------|
| `purchase.report` | Analytics: amounts, quantities, delays, by vendor/product/date |
| `purchase.bill.union` | Union view of bills and POs for matching |
| PDF: RFQ Template | Printable Request for Quotation |
| PDF: PO Template | Printable Purchase Order |

### 2.4 Security Groups

| Group | Purpose |
|-------|---------|
| `group_purchase_user` | Standard purchase user |
| `group_purchase_manager` | Full CRUD + settings |
| `group_warning_purchase` | See product/partner warnings |
| `group_send_reminder` | Auto-send receipt reminders |

### 2.5 Wizards

| Wizard | Purpose |
|--------|---------|
| `bill.to.po.wizard` | Add bill lines to existing PO or as down-payments |

### 2.6 Portal Controllers

| Route | Purpose |
|-------|---------|
| `/my/rfq` | List vendor's RFQs |
| `/my/purchase` | List vendor's purchase orders |
| `/my/purchase/<id>` | Single PO detail (HTML/PDF) |
| `/my/purchase/<id>/update` | JSONRPC to update delivery dates |
| `/my/purchase/<id>/download_edi` | Download EDI XML |

---

## 3. Inventory (Stock) Module — Detailed Features

**Path**: `addons/stock/`
**Manifest Dependencies**: `product`, `barcodes_gs1_nomenclature`, `digest`
**Application**: Yes (top-level module)

### 3.1 Core Models

#### 3.1.1 Stock Move (`stock.move` — 2,638 LOC) — MOST COMPLEX

**Inherits**: `mail.thread`

The fundamental unit of inventory movement. Every inventory operation creates stock moves.

**Key Fields**:
| Field | Type | Purpose |
|-------|------|---------|
| `name` | Char | Description |
| `product_id` | Many2one | Product being moved |
| `product_uom_qty` | Float | Demand quantity |
| `quantity` | Float | Done/reserved quantity |
| `product_uom` | Many2one | Unit of measure |
| `location_id` | Many2one | Source location |
| `location_dest_id` | Many2one | Destination location |
| `picking_id` | Many2one | Parent picking |
| `state` | Selection | draft/confirmed/partially_available/assigned/done/cancel |
| `date` | Datetime | Scheduled date |
| `date_deadline` | Datetime | Expected delivery deadline |
| `origin` | Char | Source document reference |
| `group_id` | Many2one | Procurement group |
| `rule_id` | Many2one | Stock rule that created this move |
| `move_dest_ids` | Many2many | Downstream moves (chaining) |
| `move_orig_ids` | Many2many | Upstream moves (chaining) |
| `move_line_ids` | One2many | Detailed move lines (lot/serial/package) |
| `price_unit` | Float | Unit price for valuation |
| `picked` | Boolean | Whether move has been picked |

**State Machine**:
```
Draft → Confirmed → Partially Available → Assigned (Reserved) → Done → Cancel
         ↑                    ↑                                      ↑
         └────────────────────┴──────────────────────────────────────┘
```

**Core Features**:

1. **Reservation System**
   - `_action_assign()` — Reserves stock for the move
   - `_do_unreserve()` — Releases reserved stock
   - `_update_reserved_quantity()` — Updates quant reservations
   - Smart reservation based on FIFO/FEFO/closest location

2. **Move Execution**
   - `_action_confirm()` — Confirms draft moves
   - `_action_done()` — Validates moves, updates quants
   - `_action_cancel()` — Cancels with cascade logic

3. **Move Chaining (Push/Pull)**
   - `_push_apply()` — Applies push rules to create downstream moves
   - Move chains: `move_orig_ids` ↔ `move_dest_ids`
   - Automatic propagation of dates, groups, priorities

4. **Quantity Management**
   - `_set_quantity_done()` — Sets done quantities on move lines
   - `_split()` — Splits a move into two (partial processing)
   - `_merge_moves()` — Merges compatible moves for efficiency

5. **Move Line Generation**
   - `_generate_move_line()` — Creates detailed operations
   - Handles lot/serial numbers, packages, owner tracking

6. **Procurement Integration**
   - `_prepare_procurement_group_vals()` — Creates procurement groups
   - `_prepare_procurement_values()` — Prepares procurement context

7. **Traceability**
   - Links to lots, serial numbers, packages
   - Full upstream/downstream document chain
   - `_get_upstream_documents_and_responsibles()`

#### 3.1.2 Stock Picking (`stock.picking` — 2,084 LOC)

**Inherits**: `mail.thread`, `mail.activity.mixin`

Groups related stock moves into a single operation (receipt, delivery, internal transfer).

**Key Fields**:
| Field | Type | Purpose |
|-------|------|---------|
| `name` | Char | Reference (auto-sequence) |
| `partner_id` | Many2one | Partner (vendor/customer) |
| `picking_type_id` | Many2one | Operation type (receipt/delivery/internal) |
| `location_id` | Many2one | Source location |
| `location_dest_id` | Many2one | Destination location |
| `move_ids` | One2many | Stock moves in this picking |
| `state` | Selection | draft/confirmed/assigned/done/cancel |
| `scheduled_date` | Datetime | Planned date |
| `date_done` | Datetime | Completion date |
| `origin` | Char | Source document |
| `backorder_id` | Many2one | Original picking (if backorder) |
| `backorder_ids` | One2many | Backorders created from this |
| `show_check_availability` | Boolean | Whether reservation button visible |
| `show_validate` | Boolean | Whether validate button visible |
| `immediate_transfer` | Boolean | No planning, direct transfer |
| `package_level_ids` | One2many | Package-level operations |
| `move_type` | Selection | direct (partial) / one (all at once) |

**Core Features**:

1. **Picking Lifecycle**
   - `action_confirm()` — Confirms the picking and its moves
   - `action_assign()` — Reserves stock
   - `button_validate()` — Validates the picking (creates backorders if needed)
   - `action_cancel()` — Cancels picking and moves
   - `action_back_to_draft()` — Resets to draft

2. **Backorder Management**
   - Automatic backorder creation for partial deliveries
   - `_create_backorder()` — Creates backorder for remaining quantities
   - `_check_backorder()` — Prompts user for backorder decision

3. **Batch Operations**
   - `action_batch_transfer()` — Groups pickings into batch
   - Wave picking support

4. **Barcode Integration**
   - `open_barcode_interface()` — Opens barcode scanning UI
   - GS1 barcode pattern support

5. **Return Processing**
   - `action_return_picking()` — Opens return wizard
   - Creates reverse moves with proper valuation

6. **Quality Checks**
   - Hook points for quality control integration
   - Check availability before validation

7. **Printing & Reports**
   - Delivery slip, picking operations, return slip
   - Package labels, product labels
   - Barcode reports

#### 3.1.3 Stock Quant (`stock.quant` — 1,696 LOC)

**The inventory truth** — represents actual stock quantities at specific locations.

**Key Fields**:
| Field | Type | Purpose |
|-------|------|---------|
| `product_id` | Many2one | Product |
| `location_id` | Many2one | Storage location |
| `lot_id` | Many2one | Lot/Serial number |
| `package_id` | Many2one | Package |
| `owner_id` | Many2one | Owner (consignment) |
| `quantity` | Float | On-hand quantity |
| `reserved_quantity` | Float | Reserved for moves |
| `available_quantity` | Float | Computed: quantity - reserved |
| `inventory_quantity` | Float | For inventory adjustments |
| `inventory_diff_quantity` | Float | Difference for adjustments |
| `value` | Monetary | Stock value (computed) |
| `storage_category_id` | Many2one | Storage category of location |

**Core Features**:

1. **Inventory Adjustments**
   - `action_apply_inventory()` — Applies counted quantities
   - `_apply_inventory()` — Creates adjustment moves
   - `_get_inventory_move_values()` — Prepares adjustment move data
   - Inventory adjustment name tracking

2. **Stock Level Queries**
   - `_gather()` — Core method to find quants (by product, location, lot, package, owner)
   - `_get_available_quantity()` — Available stock at location
   - `_update_available_quantity()` — Changes quant quantities
   - `_update_reserved_quantity()` — Updates reservation

3. **Inventory Valuation**
   - `value` — Computed stock value
   - Integration with `stock.valuation.layer`

4. **Inventory Counts**
   - `action_inventory_history()` — Shows quantity history
   - `action_stock_quant_relocate()` — Bulk relocate stock
   - Request count wizards for cycle counting

5. **FIFO/FEFO/Closest Location Ordering**
   - `_get_removal_strategy_order()` — Determines pick order
   - Supports FIFO, FEFO (expiration-based), closest location strategies

6. **Quant Relocation**
   - Bulk move quants between locations
   - Package-level relocation

#### 3.1.4 Stock Warehouse (`stock.warehouse` — 1,163 LOC)

**Key Fields**:
| Field | Type | Purpose |
|-------|------|---------|
| `name` | Char | Warehouse name |
| `code` | Char | Short code (5 chars max) |
| `partner_id` | Many2one | Warehouse address |
| `lot_stock_id` | Many2one | Default stock location |
| `view_location_id` | Many2one | Parent view location |
| `wh_input_stock_loc_id` | Many2one | Input location |
| `wh_qc_stock_loc_id` | Many2one | Quality control location |
| `wh_output_stock_loc_id` | Many2one | Output location |
| `wh_pack_stock_loc_id` | Many2one | Packing location |
| `reception_steps` | Selection | one_step / two_steps / three_steps |
| `delivery_steps` | Selection | ship_only / pick_ship / pick_pack_ship |
| `in_type_id` | Many2one | Receipt picking type |
| `out_type_id` | Many2one | Delivery picking type |
| `int_type_id` | Many2one | Internal transfer type |
| `pick_type_id` | Many2one | Pick picking type |
| `pack_type_id` | Many2one | Pack picking type |
| `route_ids` | Many2many | Routes available |
| `resupply_wh_ids` | Many2many | Inter-warehouse resupply |

**Core Features**:

1. **Multi-Step Reception**
   - 1 Step: Receive directly to stock
   - 2 Steps: Receive to input → Transfer to stock
   - 3 Steps: Receive to input → QC → Transfer to stock

2. **Multi-Step Delivery**
   - Ship Only: Direct from stock
   - Pick + Ship: Pick from stock → Ship from output
   - Pick + Pack + Ship: Pick → Pack → Ship

3. **Route & Rule Generation**
   - `_create_or_update_route()` — Auto-generates routes based on steps
   - `_create_or_update_sequences_and_picking_types()` — Creates operations
   - `_get_routes_values()` — Defines route/rule topology

4. **Inter-Warehouse Resupply**
   - `_create_resupply_routes()` — Creates routes between warehouses
   - Configurable push/pull rules

5. **Dynamic Reconfiguration**
   - Changing reception/delivery steps auto-updates routes and locations
   - `_update_location_data()` — Archives/activates locations as needed

#### 3.1.5 Stock Location (`stock.location` — 587 LOC)

**Key Fields**:
| Field | Type | Purpose |
|-------|------|---------|
| `name` | Char | Location name |
| `complete_name` | Char | Full path (computed) |
| `usage` | Selection | supplier/internal/customer/inventory/production/transit |
| `location_id` | Many2one | Parent location |
| `child_ids` | One2many | Child locations |
| `warehouse_id` | Many2one | Parent warehouse (computed) |
| `scrap_location` | Boolean | Is a scrap location |
| `return_location` | Boolean | Allows returns |
| `removal_strategy_id` | Many2one | FIFO/LIFO/FEFO strategy |
| `storage_category_id` | Many2one | Storage category |
| `quant_ids` | One2many | Stock at this location |
| `barcode` | Char | Location barcode |
| `cyclic_inventory_frequency` | Integer | Days between cycle counts |

**Location Types**:
| Type | Purpose |
|------|---------|
| `supplier` | Vendor locations (virtual) |
| `internal` | Warehouse locations (physical) |
| `customer` | Customer locations (virtual) |
| `inventory` | Inventory loss/adjustment (virtual) |
| `production` | Manufacturing (virtual) |
| `transit` | Inter-company/warehouse transit |

#### 3.1.6 Stock Lot (`stock.lot` — 417 LOC)

**Key Fields**: `name`, `product_id`, `company_id`, `quant_ids`, `product_qty`, `note`

**Features**:
- Lot/serial number tracking
- Expiration date tracking (via `stock_lot_expiry` sub-module)
- Traceability reporting
- Quantity on hand computation per lot

#### 3.1.7 Stock Rule (`stock.rule` — 752 LOC)

**Key Fields**:
| Field | Type | Purpose |
|-------|------|---------|
| `name` | Char | Rule name |
| `action` | Selection | pull/push/pull_push/buy/manufacture |
| `picking_type_id` | Many2one | Operation type |
| `location_src_id` | Many2one | Source location |
| `location_dest_id` | Many2one | Destination location |
| `route_id` | Many2one | Parent route |
| `group_propagation_option` | Selection | How to propagate procurement group |
| `auto` | Selection | manual/transparent — automation level |
| `procure_method` | Selection | make_to_stock/make_to_order |
| `delay` | Integer | Lead time (days) |

**Features**:
- Pull rules: Create moves when demand detected
- Push rules: Automatically move stock to next location
- Buy action: Creates purchase orders (via `purchase_stock`)
- Manufacture action: Creates manufacturing orders (via `mrp`)
- Lead time computation with `_get_lead_days()`

#### 3.1.8 Stock Move Line (`stock.move.line` — 1,139 LOC)

Detailed operations within a stock move — tracks lot, serial, package, and exact quantities.

**Key Fields**: `move_id`, `product_id`, `lot_id`, `lot_name`, `package_id`, `result_package_id`,
`owner_id`, `location_id`, `location_dest_id`, `quantity`, `picked`

**Features**:
- Lot/Serial assignment
- Package operations (put-in-pack)
- Source/destination package tracking
- Owner (consignment) tracking
- Barcode scanning integration

#### 3.1.9 Stock Orderpoint (`stock.warehouse.orderpoint` — 724 LOC)

Automatic reordering rules (min/max stock levels).

**Key Fields**:
| Field | Type | Purpose |
|-------|------|---------|
| `product_id` | Many2one | Product |
| `warehouse_id` | Many2one | Warehouse |
| `location_id` | Many2one | Stock location |
| `product_min_qty` | Float | Minimum stock level (trigger) |
| `product_max_qty` | Float | Maximum stock level (order up to) |
| `qty_multiple` | Float | Order multiple |
| `route_id` | Many2one | Preferred route |
| `trigger` | Selection | auto/manual |
| `qty_on_hand` | Float | Current stock (computed) |
| `qty_forecast` | Float | Forecasted stock (computed) |
| `qty_to_order` | Float | Suggested order quantity |

**Features**:
- Automatic replenishment scheduling
- Manual replenishment triggers
- Snooze functionality (delay replenishment)
- Multi-route support (buy, manufacture, transfer)
- Lead time calculations

#### 3.1.10 Stock Scrap (`stock.scrap` — 246 LOC)

**Features**:
- Scrapping products from stock
- Scrap location management
- Lot/serial scrap tracking
- Creates stock moves to scrap location

### 3.2 Product Extensions

The stock module adds significant fields to `product.template` and `product.product`:

| Field | Type | Purpose |
|-------|------|---------|
| `is_storable` | Boolean | Whether product tracks inventory |
| `tracking` | Selection | none/lot/serial — traceability |
| `qty_available` | Float | On-hand quantity |
| `virtual_available` | Float | Forecasted quantity |
| `incoming_qty` | Float | Incoming quantity |
| `outgoing_qty` | Float | Outgoing quantity |
| `free_qty` | Float | Available (unreserved) |
| `route_ids` | Many2many | Applicable routes |
| `responsible_id` | Many2one | Inventory manager |
| `weight` | Float | Product weight |
| `volume` | Float | Product volume |
| `sale_delay` | Float | Customer lead time |
| `property_stock_production` | Many2one | Production location |
| `property_stock_inventory` | Many2one | Inventory location |
| `storage_category_capacity_ids` | One2many | Storage capacity rules |
| `show_on_hand_qty_status_button` | Boolean | Show stock status |

### 3.3 Wizards (17 wizard files)

| Wizard | Purpose |
|--------|---------|
| `stock.return.picking` | Create return picking |
| `stock.backorder.confirmation` | Handle partial deliveries |
| `stock.quantity.history` | View historical inventory |
| `stock.inventory.conflict` | Resolve count conflicts |
| `stock.request.count` | Request inventory count |
| `stock.replenishment.info` | Replenishment details |
| `stock.rules.report` | Stock rules analysis |
| `stock.warn.insufficient.qty` | Low stock warnings |
| `product.replenish` | Manual replenishment |
| `product.label.layout` | Print product labels |
| `stock.orderpoint.snooze` | Snooze reorder rules |
| `stock.package.destination` | Set package destination |
| `stock.inventory.adjustment.name` | Name inventory count |
| `stock.inventory.warning` | Inventory adjustment warnings |
| `stock.label.type` | Label type selection |
| `stock.lot.label.layout` | Lot label printing |
| `stock.quant.relocate` | Bulk relocate stock |

### 3.4 Reports

| Report | Purpose |
|--------|---------|
| `stock.quantity.report` | Stock quantity analytics |
| Package barcode report | Print package barcodes |
| Lot barcode report | Print lot barcodes |
| Location barcode report | Print location barcodes |
| Picking operations | Operations detail |
| Delivery slip | Delivery documentation |
| Stock inventory report | Inventory count sheet |
| Stock rule report | Rule visualization |
| Stock reception report | Receipt documentation |
| Return slip | Return documentation |
| Traceability report | Full product traceability |
| Forecasted report | Stock forecast graph |

### 3.5 Security Groups

| Group | Purpose |
|-------|---------|
| `group_stock_user` | Basic inventory operations |
| `group_stock_manager` | Full CRUD + settings |
| `group_stock_multi_locations` | Multi-location management |
| `group_stock_multi_warehouses` | Multi-warehouse management |
| `group_tracking_lot` | Lot tracking |
| `group_production_lot` | Serial number tracking |
| `group_stock_packaging` | Package management |
| `group_stock_sign_delivery` | Delivery signature |
| `group_reception_report` | Reception report |
| `group_stock_picking_wave` | Wave picking |

---

## 4. Purchase-Stock Bridge Module

**Path**: `addons/purchase_stock/`
**Dependencies**: `stock_account`, `purchase`
**Auto-install**: Yes (installs when both purchase and stock_account are present)

### 4.1 Fields Added to Purchase Models

**On `purchase.order`**:
| Field | Purpose |
|-------|---------|
| `picking_type_id` | Incoming operation type |
| `picking_ids` | Related stock pickings |
| `incoming_picking_count` | Count of receipts |
| `group_id` | Procurement group |
| `is_shipped` | All receipts done |
| `effective_date` | First receipt completion date |
| `receipt_status` | pending/partial/full |
| `on_time_rate` | Vendor delivery performance |

**On `purchase.order.line`**:
| Field | Purpose |
|-------|---------|
| `move_ids` | Stock moves created |
| `move_dest_ids` | Downstream demand moves |
| `orderpoint_id` | Triggering reorder rule |
| `propagate_cancel` | Cancel cascade flag |
| `forecasted_issue` | Stock forecast problem |

### 4.2 Fields Added to Stock Models

**On `stock.move`**: `purchase_line_id`, `created_purchase_line_ids`
**On `stock.picking`**: `purchase_id`, `days_to_arrive`, `delay_pass`
**On `stock.warehouse`**: `buy_to_resupply`, `buy_pull_id`
**On `stock.rule`**: `action='buy'` selection value
**On `stock.warehouse.orderpoint`**: `supplier_id`, `vendor_id`, `purchase_visibility_days`
**On `stock.lot`**: `purchase_order_ids`, `purchase_order_count`

### 4.3 Key Business Logic

1. **PO → Picking Creation** (`PurchaseOrder._create_picking()`):
   - Creates procurement group
   - Creates stock picking with incoming operation type
   - Generates stock moves for each PO line
   - Confirms and assigns (reserves) moves

2. **Buy Procurement Rule** (`StockRule._run_buy()`):
   - Triggered by reorder points or MTO demand
   - Finds/creates vendor from supplier info
   - Groups procurements into POs
   - Creates/updates PO lines with quantities

3. **3-Way Matching**:
   - PO line → Stock move (receipt) → Vendor bill line
   - `qty_received` computed from done stock moves
   - Price difference handling between PO, receipt, and invoice

4. **Stock Valuation**:
   - `_get_price_unit()` — Complex pricing from PO/invoice
   - Currency conversion for multi-currency POs
   - Price difference entries for accounting

---

## 5. Stock-Account Bridge Module

**Path**: `addons/stock_account/`
**Dependencies**: `stock`, `account`
**Auto-install**: Yes

### Key Features

1. **Stock Valuation Layer** (`stock.valuation.layer`)
   - Records every valuation change
   - Supports FIFO, Average Cost, Standard Price methods
   - Links to journal entries

2. **Automated Accounting Entries**
   - Stock input/output accounts
   - Inventory valuation account
   - Price difference accounts
   - Currency exchange difference

3. **Product Valuation Settings**
   - Manual vs automated valuation
   - Costing method: Standard, Average, FIFO
   - Category-level accounting configuration

4. **Anglo-Saxon Accounting**
   - Cost of Goods Sold on delivery
   - Interim accounts for pending invoices

---

## 6. Full Dependency Tree

### Minimum Required Modules (23 total)

```
Level 0 (Core):
  └── base

Level 1 (Framework):
  ├── web
  └── bus (auto-install)

Level 2 (Utilities):
  ├── uom
  ├── base_setup (auto-install)
  └── html_editor (auto-install)

Level 3 (Communication):
  ├── mail
  ├── web_tour
  └── auth_signup (auto-install)

Level 4 (Business Foundation):
  ├── product
  ├── analytic
  ├── resource
  ├── http_routing
  └── web_editor (auto-install)

Level 5 (Business Services):
  ├── portal
  ├── onboarding
  ├── digest
  ├── barcodes
  └── barcodes_gs1_nomenclature

Level 6 (Business Applications):
  ├── account
  └── stock

Level 7 (Bridge):
  └── stock_account (auto-install)

Level 8 (Target Applications):
  ├── purchase
  └── purchase_stock (auto-install)
```

### Module Sizes in Dependency Chain

| Module | LOC (approx) | Essential for Standalone? |
|--------|-------------|--------------------------|
| base | ~100K+ | YES — Odoo core |
| web | ~80K+ | YES — Web client |
| bus | ~5K | YES — Real-time updates |
| uom | ~2K | YES — Unit of measure |
| mail | ~30K+ | PARTIAL — Chatter, activities |
| product | ~15K | YES — Product catalog |
| account | ~60K+ | PARTIAL — Only for purchase billing |
| stock | ~56K | YES — Inventory core |
| purchase | ~11K | YES — Purchase core |
| stock_account | ~12K | OPTIONAL — Only for valuation |
| purchase_stock | ~17K | YES — Links purchase to stock |

---

## 7. Feature Classification for Standalone Usage

### 7.1 ESSENTIAL Features (Must Keep)

**Purchase**:
- Purchase order CRUD and state machine
- PO line management with pricing
- Vendor management
- Basic tax computation
- PO confirmation and approval

**Stock**:
- Stock move creation and execution
- Stock picking lifecycle
- Quant management (on-hand tracking)
- Location hierarchy
- Warehouse configuration
- Basic reservation system

**Bridge**:
- PO → Picking creation
- Receipt → PO line qty_received update
- Buy procurement rule (auto-PO from reorder points)

### 7.2 IMPORTANT but Removable Features

| Feature | Module | Impact of Removal |
|---------|--------|-------------------|
| Two-step approval | purchase | Simplifies workflow |
| Portal access | purchase | No vendor self-service |
| RFQ merging | purchase | No duplicate consolidation |
| Receipt reminders | purchase | No auto-emails |
| Dashboard stats | purchase | No KPI display |
| EDI support | purchase | No electronic document exchange |
| Bill matching | purchase | Manual invoice matching only |
| Down-payments | purchase | No advance payments |
| Multi-step reception | stock | Direct stock only |
| Multi-step delivery | stock | Direct ship only |
| Package management | stock | No package tracking |
| Wave picking | stock | No batch operations |
| Storage categories | stock | No storage optimization |
| Cycle counting | stock | No automated counts |
| Inter-warehouse resupply | stock | Single warehouse only |
| Forecasting graph | stock | No visual forecasts |
| Return processing | stock | Manual adjustment only |

### 7.3 OPTIONAL Features (Can Remove for Lightweight)

| Feature | Module | Lines Saved (est.) |
|---------|--------|--------------------|
| Analytic accounting | purchase | ~200 |
| Product catalog browser | purchase | ~150 |
| Barcode scanning | stock | ~500 |
| GS1 nomenclature | stock | ~300 |
| Scrap management | stock | ~250 |
| Package levels | stock | ~210 |
| Storage categories | stock | ~75 |
| Product strategy | stock | ~190 |
| Stock valuation | stock_account | ~12,000 (entire module) |
| Digest/KPI | both | ~100 |

---

## 8. Optimization Recommendations

### 8.1 Dependency Reduction Strategy

**Tier 1 — Maximum Reduction** (Remove accounting entirely):
```
Remove: account, stock_account, analytic, digest, onboarding
Keep: base, web, bus, uom, mail, product, stock, purchase (custom bridge)
Result: ~8 modules instead of 23
Tradeoff: No invoicing, no valuation, no financial reporting
```

**Tier 2 — Balanced Reduction** (Keep accounting, remove extras):
```
Remove: barcodes_gs1_nomenclature, digest, web_editor, web_tour
Keep: 19 modules
Result: Remove barcode scanning, KPIs, rich text editing
Tradeoff: No barcode operations, simpler UI
```

**Tier 3 — Feature Trimming** (Keep all modules, trim features):
```
Keep all 23 modules but disable/remove:
- Portal controllers and templates
- Multi-step reception/delivery (force 1-step)
- Wave picking, batch transfers
- Package management
- Storage categories
- Inter-warehouse resupply
- RFQ merging and duplicate detection
- Receipt reminder cron
- EDI support
Result: Same module count but ~30-40% less code within modules
```

### 8.2 Code-Level Optimizations

1. **Reduce Computed Fields**:
   - Many computed fields with `store=True` trigger recomputation cascades
   - Remove non-essential computed fields (dashboard stats, forecast flags)
   - Convert expensive computations to on-demand methods

2. **Simplify Stock Move** (2,638 LOC → ~1,500 LOC est.):
   - Remove push rule logic if not using multi-step
   - Simplify merge logic
   - Remove procurement propagation for single-warehouse
   - Simplify reservation for basic FIFO only

3. **Simplify Stock Picking** (2,084 LOC → ~1,200 LOC est.):
   - Remove backorder logic if always processing full quantities
   - Remove batch/wave picking
   - Remove package-level operations
   - Simplify validation flow

4. **Simplify Stock Quant** (1,696 LOC → ~800 LOC est.):
   - Remove FEFO/closest location strategies (keep FIFO only)
   - Simplify inventory adjustment flow
   - Remove relocation wizard
   - Simplify cycle counting

5. **Simplify Purchase Order** (1,373 LOC → ~800 LOC est.):
   - Remove portal integration
   - Remove two-step approval
   - Remove RFQ merging
   - Remove receipt reminders
   - Simplify dashboard

6. **Simplify Warehouse** (1,163 LOC → ~400 LOC est.):
   - Force single-step reception/delivery
   - Remove inter-warehouse resupply
   - Remove dynamic route reconfiguration
   - Static warehouse setup only

### 8.3 Performance Optimizations

1. **Database Queries**:
   - Stock move `_action_assign()` does multiple queries per product — batch these
   - Quant `_gather()` is called frequently — add caching layer
   - Purchase report uses complex SQL joins — pre-aggregate

2. **Computed Field Cascades**:
   - `purchase.order.amount_total` triggers on every line change
   - `stock.quant.available_quantity` recomputes on every move
   - Use `compute_sudo=True` where security context not needed

3. **Reduce ORM Overhead**:
   - Stock move merge uses heavy ORM operations — use raw SQL for large batches
   - Picking validation creates many records — batch create

4. **Cron Job Optimization**:
   - Receipt reminder cron scans all POs — add date index
   - Orderpoint scheduler can be heavy — limit scope per run

### 8.4 Standalone Architecture Recommendation

For a lightweight Purchase + Inventory system:

```
┌─────────────────────────────────────────────┐
│              Odoo Core (base + web)          │
├─────────────────────────────────────────────┤
│  product (catalog)  │  uom (units)          │
├─────────────────────────────────────────────┤
│     stock_lite                               │
│  ┌─────────────────────────────────────┐    │
│  │ stock.location (simplified)          │    │
│  │ stock.warehouse (1-step only)        │    │
│  │ stock.move (no push/pull chains)     │    │
│  │ stock.picking (no backorders)        │    │
│  │ stock.quant (FIFO only)              │    │
│  │ stock.lot (basic tracking)           │    │
│  └─────────────────────────────────────┘    │
├─────────────────────────────────────────────┤
│     purchase_lite                            │
│  ┌─────────────────────────────────────┐    │
│  │ purchase.order (no 2-step, no portal)│    │
│  │ purchase.order.line (basic pricing)  │    │
│  │ Direct PO → Receipt creation         │    │
│  │ Basic vendor management              │    │
│  └─────────────────────────────────────┘    │
├─────────────────────────────────────────────┤
│  account (optional — only if billing needed) │
└─────────────────────────────────────────────┘

Estimated LOC: ~25,000-30,000 (vs ~96,000 original = ~70% reduction)
Estimated modules: 8-10 (vs 23 original)
```

### 8.5 Key Files to Focus On for Optimization

| Priority | File | Action |
|----------|------|--------|
| P0 | `stock/models/stock_move.py` | Heavy refactor — largest & most complex |
| P0 | `stock/models/stock_picking.py` | Simplify validation & backorder |
| P0 | `stock/models/stock_quant.py` | Simplify reservation & strategies |
| P1 | `stock/models/stock_warehouse.py` | Force 1-step, remove dynamic routes |
| P1 | `purchase/models/purchase_order.py` | Remove portal, reminders, merge |
| P1 | `purchase_stock/models/stock_rule.py` | Simplify buy rule |
| P2 | `stock/models/stock_move_line.py` | Simplify package/owner tracking |
| P2 | `stock/models/stock_rule.py` | Remove unused action types |
| P2 | `purchase/models/account_invoice.py` | Simplify matching algorithm |
| P3 | All wizard files | Remove non-essential wizards |
| P3 | All report files | Keep only essential reports |

---

## Summary

The combined Purchase + Inventory codebase spans **~96,000 lines** across **429 source files** in 4 core modules
plus 19 dependency modules. The Inventory module alone accounts for ~58% of this code due to the complexity
of stock moves, picking workflows, quant management, and warehouse configuration.

**For standalone usage**, the most impactful optimizations are:
1. **Force single-step warehouse operations** — eliminates ~40% of warehouse/route complexity
2. **Remove portal, EDI, and reminders** — eliminates ~15% of purchase code
3. **Remove stock valuation** (if accounting not needed) — eliminates entire `stock_account` module
4. **Simplify reservation to FIFO only** — reduces quant complexity by ~50%
5. **Remove package management** — eliminates package levels, types, and related wizard code

These changes together can achieve an estimated **60-70% code reduction** while maintaining core
purchase-to-receipt functionality.
