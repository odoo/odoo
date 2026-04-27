import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { formatFloat } from "@web/core/utils/numbers";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    get quantityStr() {
        const unit = this.product_id.uom_id;
        if (this.config.isCertified && unit?.rounding && unit.id === this.config._unit_uom_id) {
            const decimals = this.models["decimal.precision"].find(
                (dp) => dp.name === "Product Unit of Measure"
            ).digits;
            return formatFloat(this.qty, {
                digits: [69, decimals],
                trailingZeros: false,
            });
        }

        return super.quantityStr;
    },

    getDisplayData() {
        return {
            ...super.getDisplayData(...arguments),
            showUnit: this.product_id.uom_id.id !== 1,
        };
    },
});
