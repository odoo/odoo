import { registry } from "@web/core/registry";
import { Base } from "@point_of_sale/app/models/related_models";
import { _t } from "@web/core/l10n/translation";

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
    get startDateForDuration() {
        const order = this.getOrder();
        return order ? order.create_date : null;
    }
    orderDuration() {
        const startTime = this.startDateForDuration;
        if (!startTime) {
            return false;
        }

        const order = this.getOrder();
        const endTime = order && order.state !== "draft" ? order.date_order : luxon.DateTime.now();
        if (!startTime || !endTime) {
            return false;
        }

        const diff = endTime.diff(startTime, ["hours", "minutes"]).toObject();
        const hours = Math.floor(diff.hours || 0);
        const minutes = Math.floor(diff.minutes || 0);

        if ((!hours && !minutes) || hours < 0 || minutes < 0) {
            return false;
        }

        if (hours && minutes) {
            return _t("%sh%s'", hours, minutes);
        } else if (hours) {
            return _t("%sh", hours);
        }

        return _t("%s'", minutes);
    }
    setParent(parent) {
        if (parent && (parent.id === this.id || parent.isParent(this))) {
            return;
        }
        this.parent_id = parent;
    }
}
registry.category("pos_available_models").add(RestaurantTable.pythonModel, RestaurantTable);
