import { patch } from "@web/core/utils/patch";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";

patch(Orderline.prototype, {
    get infoListClasses() {
        if (this.line.packLotLines?.length) {
            return "gap-2 mt-1";
        }
        return super.infoListClasses;
    },

    get lineScreenValues() {
        const values = super.lineScreenValues;
        if (!Object.keys(values).length) {
            return values;
        }
        values.lotLines =
            ["lot", "serial"].includes(this.line.product_id.tracking) &&
            (this.line.packLotLines || []);
        return values;
    },
});
