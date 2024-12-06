import { registry } from "@web/core/registry";
import { Base } from "@point_of_sale/app/models/related_models";

export class RestaurantTable extends Base {
    static pythonModel = "restaurant.table";

    setup(vals) {
        super.setup(vals);

        this.table_number = vals.table_number || 0;
        this.uiState = {
            initialPosition: {},
            orderCount: 0,
            changeCount: 0,
            skipCount: 0,
        };
    }
    isParent(t) {
        return t.parent_id && (t.parent_id.id === this.id || this.isParent(t.parent_id));
    }
    getParent() {
        return this.parent_id?.getParent() || this;
    }
    getParentSide() {
        if (!this.parent_id) {
            return;
        }
        const dx = this.position_h - this.parent_id.getX();
        const dy = this.position_v - this.parent_id.getY();
        if (Math.abs(dx) > Math.abs(dy)) {
            return dx < 0 ? "right" : "left";
        }
        return dy > 0 ? "bottom" : "top";
    }
    getX() {
        if (!this.parent_id) {
            return this.position_h;
        }
        const parent_side = this.parent_side || this.getParentSide();
        if (["top", "bottom"].includes(parent_side)) {
            return this.parent_id.getX();
        }
        if (parent_side === "left") {
            return this.parent_id.getX() + this.parent_id.width;
        }
        return this.parent_id.getX() - this.width;
    }
    getY() {
        if (!this.parent_id) {
            return this.position_v;
        }
        const parent_side = this.parent_side || this.getParentSide();
        this.parent_side = parent_side;
        if (["left", "right"].includes(parent_side)) {
            return this.parent_id.getY();
        }
        if (parent_side === "bottom") {
            return this.parent_id.getY() + this.parent_id.height;
        }
        return this.parent_id.getY() - this.height;
    }
    getCenter() {
        return {
            x: this.getX() + this.width / 2,
            y: this.getY() + this.height / 2,
        };
    }
    get orders() {
        return this.models["pos.order"].filter(
            (o) =>
                o.table_id?.id === this.id &&
                // Include the orders that are in tipping state.
                (!o.finalized || o.uiState.screen_data?.value?.name === "TipScreen")
        );
    }
    getOrder() {
        return (
            this.parent_id?.getOrder?.() || this["<-pos.order.table_id"].find((o) => !o.finalized)
        );
    }
    setPositionAsIfLinked(parent, side) {
        this.parent_id = parent;
        this.parent_side = side;
        this.position_h = this.getX();
        this.position_v = this.getY();
        this.parent_id = null;
    }
    getName() {
        return this.table_number.toString();
    }
}
registry.category("pos_available_models").add(RestaurantTable.pythonModel, RestaurantTable);
