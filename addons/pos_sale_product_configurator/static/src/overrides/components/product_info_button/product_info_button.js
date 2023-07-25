/** @odoo-module */

import { ProductInfoButton } from "@point_of_sale/app/screens/product_screen/control_buttons/product_info_button/product_info_button";
import { patch } from "@web/core/utils/patch";

patch(ProductInfoButton.prototype, "pos_sale_product_configurator.ProductInfoButton", {
    hasOptionalProduct() {
        const orderline = this.pos.get_order().get_selected_orderline();
        if (orderline) {
            const optionalProductIds = orderline.product.optional_product_ids;
            return Object.values(this.pos.db.product_by_id).find((p) =>
                optionalProductIds.includes(p.product_tmpl_id)
            );
        }
        return false;
    },
});
