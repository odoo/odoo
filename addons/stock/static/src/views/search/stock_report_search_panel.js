import { SearchPanel } from "@web/search/search_panel/search_panel";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { proxy } from "@odoo/owl";

export class StockReportSearchPanel extends SearchPanel {
    static template = "stock.StockReportSearchPanel";
    static components = { ...SearchPanel.components, DateTimeInput };

    setup() {
        super.setup(...arguments);
        this.selectedWarehouse = false;
        this.dateState = proxy({ inventoryDate: false });
    }

    //---------------------------------------------------------------------
    // Actions / Getters
    //---------------------------------------------------------------------

    get defaultDate() {
        return luxon.DateTime.now().startOf("minute");
    }

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

    onDateApply(date) {
        this.dateState.inventoryDate = date;
        const isoDate = date ? date.toUTC().toFormat("yyyy-MM-dd HH:mm:ss") : false;
        this.env.searchModel.applyDateContext(isoDate);
    }

    clearDate() {
        this.dateState.inventoryDate = false;
        this.env.searchModel.applyDateContext(false);
    }
}
