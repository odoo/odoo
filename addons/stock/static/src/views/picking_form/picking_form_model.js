/** @odoo-module **/

import { Record, RelationalModel } from "@web/views/basic_relational_model";

export class StockPickingAutoSaveRecord extends Record {
    async saveAndOpenActionShowDetails() {
        this._lock = true;
        await new Promise((resolve) => {
            this.model.env.bus.trigger("STOCK_MOVE:UPDATED", { resolve });
        });
        this.model.env.bus.trigger("STOCK_MOVE:SAVED", {
            id: this.data.id,
            product_id: this.data.product_id,
        });
        this._lock = false;
    }

    async update(changes) {
        const record_prom = super.update(changes);
        if (this._lock || this.resModel !== "stock.move" || !("quantity_done" in changes)) {
            return record_prom;
        }
        this._lock = true;
        await record_prom;
        console.log(this)
        console.log(this.data.picking_id)
        if (this.data.picking_id) {
            await this.save()
        } else {
            await new Promise((resolve) => {
                this.model.env.bus.trigger("STOCK_MOVE:UPDATED", { resolve });
            });
        }
        console.log(this)
        this._lock = false;
        return record_prom;
     }
}

export class StockPickingModel extends RelationalModel {}
StockPickingModel.Record = StockPickingAutoSaveRecord;
