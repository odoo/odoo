import { patch } from "@web/core/utils/patch";
import { PreparationDisplay } from "@pos_preparation_display/app/models/preparation_display";

patch(PreparationDisplay.prototype, {
    async setup() {
        this.tables = {};
        await super.setup(...arguments);
    },
    filterOrders() {
        this.tables = {};
        super.filterOrders(...arguments);

        for (const order of this.filteredOrders) {
            if (!this.tables[order.table.id]) {
                this.tables[order.table.id] = [];
            }
            this.tables[order.table.id].push(order);
        }
    },
});
