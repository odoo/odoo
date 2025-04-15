/** @odoo-module **/

import { SearchPanel } from "@web/search/search_panel/search_panel";

export class StockReportSearchPanel extends SearchPanel {
    setup() {
        super.setup(...arguments);
        this.selectedWarehouse = false;
    }

    //---------------------------------------------------------------------
    // Actions / Getters
    //---------------------------------------------------------------------

    get warehouses() {
        return this.env.searchModel.getWarehouses();
    }

    clearWarehouseContext() {
        this.env.searchModel.clearWarehouseContext();
        this.selectedWarehouse = null;
    }

    applyWarehouseContext(warehouse_id) {
        this.env.searchModel.applyWarehouseContext(warehouse_id);
        this.selectedWarehouse = warehouse_id;
    }
}

StockReportSearchPanel.template = "stock.StockReportSearchPanel";
