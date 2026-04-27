/** @odoo-module */

import { StockBarcodeKanbanController } from '@stock_barcode/kanban/stock_barcode_kanban_controller';
import { patch } from "@web/core/utils/patch";

patch(StockBarcodeKanbanController.prototype, {
    setup() {
        super.setup(...arguments);
    },

    /**
     * Add a new batch picking from barcode
     *
     * @private
     * @override
     */
    async createRecord() {
        if (this.props.resModel === "stock.picking.batch") {
            const action = await this.model.orm.call(
                "stock.picking.batch",
                "open_new_batch_picking",
                [], { context: this.props.context }
            );
            if (action) {
                return this.actionService.doAction(action);
            }
        }
        return super.createRecord(...arguments);
    },
});
