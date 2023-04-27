/** @odoo-module */

import { ProductInfoButton } from "@point_of_sale/js/Screens/ProductScreen/ControlButtons/ProductInfoButton";
import { patch } from "@web/core/utils/patch";

patch(ProductInfoButton.prototype, "pos_sale_product_configurator.ProductInfoButton", {
    hasOptionalProduct() {
        const orderline = this.pos.globalState.get_order().get_selected_orderline();
        if (orderline) {
            const optionalProductIds = orderline.product.optional_product_ids;
            return Object.values(this.pos.globalState.db.product_by_id).find((p) =>
                optionalProductIds.includes(p.product_tmpl_id)
            );
        }
        return false;
    },
});
