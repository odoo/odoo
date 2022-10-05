/** @odoo-module **/

import { Record, RelationalModel } from "@web/views/basic_relational_model";

export class StockPickingAutoSaveRecord extends Record {
    setup(params, state) {
        super.setup(params, state);
    }

    async saveAndOpenDetails() {
        await new Promise((resolve) => {
            this.model.env.bus.trigger("STOCK_MOVE:UPDATED", { resolve });
        });
        await new Promise((resolve) => {
            this.model.env.bus.trigger("STOCK_MOVE:SAVED", {
                id: this.data.id,
                product_id: this.data.product_id,
                resolve,
            });
        });
    }
}

export class StockPickingModel extends RelationalModel {}
StockPickingModel.Record = StockPickingAutoSaveRecord;
