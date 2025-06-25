import { ProductInfoPopup } from "@point_of_sale/app/screens/product_screen/product_info_popup/product_info_popup";
import { patch } from "@web/core/utils/patch";

patch(ProductInfoPopup.prototype, {
    async switchSelfAvailability() {
        await this.pos.data.write("product.product", [this.props.product.id], {
            self_order_available: !this.props.product.self_order_available,
        });
    },
});
