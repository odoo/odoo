import { ProductInfoPopup } from "@point_of_sale/app/components/popups/product_info_popup/product_info_popup";
import { patch } from "@web/core/utils/patch";

patch(ProductInfoPopup.prototype, {
    async switchSelfAvailability() {
        await this.pos.data.write("product.template", [this.props.productTemplate.id], {
            self_order_available: !this.props.productTemplate.self_order_available,
        });
    },
    showSelfOrderToggle() {
        return (
            this.pos.config.self_ordering_mode != "nothing" &&
            (this.pos.config.module_pos_hr
                ? this.pos.cashier._role === "manager" && this.pos.allowProductCreation()
                : this.pos.allowProductCreation())
        );
    },
});
