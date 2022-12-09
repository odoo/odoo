/** @odoo-module */

import PosComponent from "@point_of_sale/js/PosComponent";
import ProductScreen from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { useListener } from "@web/core/utils/hooks";
import Registries from "@point_of_sale/js/Registries";
import { ConnectionLostError, ConnectionAbortedError } from "@web/core/network/rpc_service";
import { identifyError } from "@point_of_sale/js/utils";

class ProductInfoButton extends PosComponent {
    setup() {
        super.setup();
        useListener("click", this.onClick);
    }
    async onClick() {
        const orderline = this.env.pos.get_order().get_selected_orderline();
        if (orderline) {
            const product = orderline.get_product();
            const quantity = orderline.get_quantity();
            try {
                const info = await this.env.pos.getProductInfo(product, quantity);
                this.showPopup("ProductInfoPopup", { info: info, product: product });
            } catch (e) {
                if (identifyError(e) instanceof ConnectionLostError || ConnectionAbortedError) {
                    this.showPopup("OfflineErrorPopup", {
                        title: this.env._t("Network Error"),
                        body: this.env._t("Cannot access product information screen if offline."),
                    });
                } else {
                    this.showPopup("ErrorPopup", {
                        title: this.env._t("Unknown error"),
                        body: this.env._t(
                            "An unknown error prevents us from loading product information."
                        ),
                    });
                }
            }
        }
    }
}
ProductInfoButton.template = "ProductInfoButton";

ProductScreen.addControlButton({
    component: ProductInfoButton,
    position: ["before", "SetFiscalPositionButton"],
});

Registries.Component.add(ProductInfoButton);

export default ProductInfoButton;
