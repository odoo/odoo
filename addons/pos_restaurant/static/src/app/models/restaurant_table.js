import { registry } from "@web/core/registry";
import { Base } from "@point_of_sale/app/models/related_models";

export class RestaurantTable extends Base {
    static pythonModel = "restaurant.table";

    setup(vals) {
        super.setup(vals);
        this.table_number = vals.table_number || 0;
    }
    initState() {
        super.initState();
        this.uiState = {
            orderCount: 0,
            changeCount: 0,
        };
    }
    isParent(t) {
        return t.parent_id && (t.parent_id.id === this.id || this.isParent(t.parent_id));
    }
    getParent() {
        return this.parent_id?.getParent() || this;
    }
    getOrders() {
        return this.models["pos.order"].filter(
            (o) =>
                o.table_id?.id === this.id &&
                // Include the orders that are in tipping state.
                (!o.finalized || o.uiState.screen_data?.value?.name === "TipScreen")
        );
    }
    getOrder() {
        return (
            this.parent_id?.getOrder?.() ||
            this.backLink("<-pos.order.table_id").find((o) => !o.finalized)
        );
    }
    getName() {
        return this.table_number.toString();
    }
    get children() {
        return this.backLink("<-restaurant.table.parent_id");
    }
    get rootTable() {
        let table = this;
        while (table.parent_id) {
            table = table.parent_id;
        }
        return table;
    }
}
registry.category("pos_available_models").add(RestaurantTable.pythonModel, RestaurantTable);
