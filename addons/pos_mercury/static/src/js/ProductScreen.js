/** @odoo-module */

import ProductScreen from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import Registries from "@point_of_sale/js/Registries";
import { useBarcodeReader } from "@point_of_sale/js/custom_hooks";

const PosMercuryProductScreen = (ProductScreen) =>
    class extends ProductScreen {
        setup() {
            super.setup();
            useBarcodeReader({
                credit: this.credit_error_action,
            });
        }
        credit_error_action() {
            this.showPopup("ErrorPopup", {
                body: this.env._t("Go to payment screen to use cards"),
            });
        }
    };

Registries.Component.extend(ProductScreen, PosMercuryProductScreen);

export default ProductScreen;
