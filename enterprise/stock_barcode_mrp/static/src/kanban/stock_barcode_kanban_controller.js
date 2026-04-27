/** @odoo-module */

import { StockBarcodeKanbanController } from '@stock_barcode/kanban/stock_barcode_kanban_controller';
import { patch } from "@web/core/utils/patch";


patch(StockBarcodeKanbanController.prototype, {
    createRecord() {
        if (this.props.resModel === "mrp.production") {
            return this.actionService.doAction("stock_barcode_mrp.stock_barcode_mo_client_action", {
                additionalContext: { default_picking_type_id: this.props.context.active_id },
            });
        }
        return super.createRecord(...arguments);
    },

    openRecord(record) {
        if (this.props.resModel === 'mrp.production') {
            return this.actionService.doAction('stock_barcode_mrp.stock_barcode_mo_client_action', {
                additionalContext: { active_id: record.resId },
            });
        }
        return super.openRecord(...arguments);
    },
});
