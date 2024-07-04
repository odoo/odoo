import { registry } from "@web/core/registry";
import { Base } from "@point_of_sale/app/models/related_models";

export class RestaurantTable extends Base {
    static pythonModel = "restaurant.table";

    setup(vals) {
        super.setup(vals);

        this.uiState = {
            orderCount: 0,
            changeCount: 0,
            skipCount: 0,
        };
    }
    isParent(t) {
        return t.parent_id && (t.parent_id.id === this.id || this.isParent(t.parent_id));
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
        const parent_side = this.getParentSide();
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
        const parent_side = this.getParentSide();
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
}

registry.category("pos_available_models").add(RestaurantTable.pythonModel, RestaurantTable);
