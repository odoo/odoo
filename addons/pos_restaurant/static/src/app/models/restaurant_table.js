import { registry } from "@web/core/registry";
import { Base } from "@point_of_sale/app/models/related_models";

const { DateTime, Interval } = luxon;

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
    startDateForDuration() {
        const order = this.getOrder();
        if (order?.getFiredCourses.length) {
            return order.getFiredCourses[0][1];
        }
        return order?.create_date;
    }
    orderDuration() {
        const startTime = this.startDateForDuration();
        if (!startTime) {
            return false;
        }

        const order = this.getOrder();
        const endTime = order && order.state !== "draft" ? order.date_order : DateTime.now();
        if (!startTime || !endTime) {
            return false;
        }

        const duration = Interval.fromDateTimes(startTime, endTime).toDuration([
            "hours",
            "minutes",
        ]);
        if (!duration.isValid || (!duration.hours && !duration.minutes) || duration.minutes < 1) {
            return false;
        }

        return duration.hours ? duration.toFormat("h'h'm''") : duration.toFormat("m''");
    }
    setParent(parent) {
        if (parent && (parent.id === this.id || parent.isParent(this))) {
            return;
        }
        this.parent_id = parent;
    }
}
registry.category("pos_available_models").add(RestaurantTable.pythonModel, RestaurantTable);
