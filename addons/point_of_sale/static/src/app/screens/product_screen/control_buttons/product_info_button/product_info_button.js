/** @odoo-module */

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { useService } from "@web/core/utils/hooks";
import { ProductInfoPopup } from "@point_of_sale/app/screens/product_screen/product_info_popup/product_info_popup";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";

export class ProductInfoButton extends Component {
    static template = "point_of_sale.ProductInfoButton";

    setup() {
        this.pos = usePos();
        this.popup = useService("popup");
        this.pos = usePos();
    }
    async click() {
        const orderline = this.pos.get_order().get_selected_orderline();
        if (orderline) {
            const product = orderline.get_product();
            const quantity = orderline.get_quantity();
            const info = await this.pos.getProductInfo(product, quantity);
            this.popup.add(ProductInfoPopup, { info: info, product: product });
        }
    }
}

ProductScreen.addControlButton({
    component: ProductInfoButton,
    position: ["before", "SetFiscalPositionButton"],
});
