import { ProductInfoPopup } from "@point_of_sale/app/components/popups/product_info_popup/product_info_popup";
import { patch } from "@web/core/utils/patch";

patch(ProductInfoPopup.prototype, {
    get allowProductEdition() {
        return this.pos.config.module_pos_hr
            ? this.pos.cashier._role === "manager" && super.allowProductEdition
            : super.allowProductEdition;
    },
});
