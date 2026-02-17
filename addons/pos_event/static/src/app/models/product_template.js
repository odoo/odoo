import { ProductTemplate } from "@point_of_sale/app/models/product_template";
import { patch } from "@web/core/utils/patch";

patch(ProductTemplate.prototype, {
    get event_id() {
        if (!this._event_id) {
            return false;
        }

        return this.models["event.event"].get(this._event_id);
    },
    set event_id(event) {
        this._event_id = event ? event.id : undefined;
    },
    get canBeDisplayed() {
        if (this.event_id) {
            return true;
        }
        return super.canBeDisplayed;
    },
});
