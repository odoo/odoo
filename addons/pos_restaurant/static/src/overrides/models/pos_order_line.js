import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    setup() {
        super.setup(...arguments);
        this.note = this.note || "";
    },
    //@override
    clone() {
        const orderline = super.clone(...arguments);
        orderline.note = this.note;
        return orderline;
    },
    get_line_diff_hash() {
        if (this.getNote()) {
            return this.id + "|" + this.getNote();
        } else {
            return "" + this.id;
        }
    },
    toggleSkipChange() {
        if (this.uiState.hasChange || this.skip_change) {
            this.skip_change = !this.skip_change;
        }
    },
    getDisplayClasses() {
        return {
            ...super.getDisplayClasses(),
            "has-change text-success border-start border-success border-4":
                this.uiState.hasChange && this.config.module_pos_restaurant,
            "skip-change text-primary border-start border-primary border-4":
                this.skip_change && this.config.module_pos_restaurant,
        };
    },
    compute_fixed_price(price) {
        if (
            this.order_id &&
            this.config.takeaway &&
            this.config.takeaway_fp_id?.id === this.order_id.fiscal_position_id?.id &&
            this.order_id.takeaway
        ) {
            price = this.product_id.get_price(this.config.pricelist_id, 1, this.price_extra);
            return price;
        }
        return super.compute_fixed_price(...arguments);
    },
});
