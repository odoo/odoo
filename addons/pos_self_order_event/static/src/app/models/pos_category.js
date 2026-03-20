import { PosCategory } from "@point_of_sale/app/models/pos_category";
import { patch } from "@web/core/utils/patch";

patch(PosCategory.prototype, {
    get associatedProducts() {
        const products = super.associatedProducts;
        return products.filter((p) => p.service_tracking !== "event");
    },
});
