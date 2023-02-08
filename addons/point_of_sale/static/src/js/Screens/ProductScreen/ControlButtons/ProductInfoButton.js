/** @odoo-module */

import { ProductScreen } from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { useService } from "@web/core/utils/hooks";
import { ProductInfoPopup } from "@point_of_sale/js/Popups/ProductInfoPopup";
import { Component } from "@odoo/owl";

export class ProductInfoButton extends Component {
    static template = "ProductInfoButton";

    setup() {
        super.setup();
        this.popup = useService("popup");
    }
    async click() {
        const orderline = this.env.pos.get_order().get_selected_orderline();
        if (orderline) {
            const product = orderline.get_product();
            const quantity = orderline.get_quantity();
            const info = await this.env.pos.getProductInfo(product, quantity);
            this.popup.add(ProductInfoPopup, { info: info, product: product });
        }
    }
}

ProductScreen.addControlButton({
    component: ProductInfoButton,
    position: ["before", "SetFiscalPositionButton"],
});
