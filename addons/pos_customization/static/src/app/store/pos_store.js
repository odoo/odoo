import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    async addLineToCurrentOrder(vals, opts = {}, configure = true) {
        if (vals.product_id && typeof vals.product_id === "object" && vals.product_id.id) {
            const productId = vals.product_id.id;
            const product =
                this.models["product.product"].getBy("id", productId) || vals.product_id;
            vals = { ...vals, product_id: product };
        }

        return await super.addLineToCurrentOrder(vals, opts, configure);
    },
    async getProductInfo(product, quantity, priceExtra = 0) {
        return await super.getProductInfo(product, quantity, priceExtra);
    },
});
