import { patch } from "@web/core/utils/patch";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";

patch(Orderline.prototype, {
    get lineScreenValues() {
        const line_screen_values = super.lineScreenValues;
        return {
            ...line_screen_values,
            lotLines:
                ["lot", "serial"].includes(this.line?.product_id?.tracking) &&
                (this.line?.packLotLines || []),
        };
    },
});
