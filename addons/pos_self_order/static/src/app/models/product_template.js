import { ProductTemplate } from "@point_of_sale/app/models/product_template";
import { patch } from "@web/core/utils/patch";

patch(ProductTemplate.prototype, {
    get config() {
        return this.models["pos.self.order.config"].getFirst();
    },
});
