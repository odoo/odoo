/** @odoo-module */

import { ProductInfoPopup } from "@point_of_sale/app/screens/product_screen/product_info_popup/product_info_popup";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(ProductInfoPopup.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
    },
    async switchSelfAvailability() {
        await this.orm.write("product.product", [this.props.product.id], {
            self_order_available: !this.props.product.self_order_available,
        });
        this.props.product.self_order_available = !this.props.product.self_order_available;
    },
});
