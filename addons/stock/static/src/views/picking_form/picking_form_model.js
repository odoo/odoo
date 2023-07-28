/** @odoo-module **/

import { RelationalModel } from "@web/model/relational_model/relational_model";
import { Record } from "@web/model/relational_model/record";

export class StockPickingAutoSaveRecord extends Record {
    async saveAndOpenDetails() {
        await new Promise((resolve) => {
            this.model.env.bus.trigger("STOCK_MOVE:UPDATED", { resolve });
        });
        await new Promise((resolve) => {
            this.model.env.bus.trigger("STOCK_MOVE:SAVED", {
                id: this.resId,
                product_id: this.data.product_id,
                resolve,
            });
        });
    }
}

export class StockPickingModel extends RelationalModel {}
StockPickingModel.Record = StockPickingAutoSaveRecord;
