/** @odoo-module */

import { kanbanView } from '@web/views/kanban/kanban_view';
import { registry } from "@web/core/registry";
import { StockBarcodeKanbanController } from './stock_barcode_kanban_controller';
import { StockBarcodeKanbanRenderer } from './stock_barcode_kanban_renderer';

export const stockBarcodeKanbanView = Object.assign({}, kanbanView, {
    Controller: StockBarcodeKanbanController,
    Renderer: StockBarcodeKanbanRenderer,
});
registry.category("views").add("stock_barcode_list_kanban", stockBarcodeKanbanView);
