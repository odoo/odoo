import { patch } from "@web/core/utils/patch";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";

patch(Orderline.prototype, {
    get lineScreenValues() {
        const values = super.lineScreenValues;
        if (this.line.isDiscountLine) {
            values.displayPriceUnit = false;
        }
        return values;
    },
});
