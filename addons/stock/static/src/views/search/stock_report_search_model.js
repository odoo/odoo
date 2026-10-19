import { SearchModel } from "@web/search/search_model";

export class StockReportSearchModel extends SearchModel {

    async load() {
        await super.load(...arguments);
        await this._loadWarehouses();
      }


    //---------------------------------------------------------------------
    // Actions / Getters
    //---------------------------------------------------------------------

    getWarehouses() {
        return this.warehouses;
    }

    async _loadWarehouses() {
        this.warehouses = await this.orm.call(
            'stock.warehouse',
            'get_current_warehouses',
            [[]],
            { context: this.context },
        );
    }

    /**
     * Clears the context of a warehouse so values calculate based on all possible
     * warehouses
     */
    clearWarehouseContext() {
        delete this.globalContext.warehouse_id;
        this._notify();
    }

    /**
     * @param {number} warehouse_id
     * Sets the context to the selected warehouse so values that take this into account
     * will recalculate based on this without filtering out any records
     */
    applyWarehouseContext(warehouse_id) {
        this.globalContext['warehouse_id'] = warehouse_id;
        this._notify();
    }

    /**
     * Sets `to_date` in the context so quantities are computed at a past date.
     * @param {string|false} date - ISO datetime string, or false to clear
     */
    applyDateContext(date) {
        if (date) {
            this.globalContext['to_date'] = date;
        } else {
            delete this.globalContext['to_date'];
        }
        this._notify();
    }
}
