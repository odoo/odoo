import { Component } from "@odoo/owl";
import { ProductBox } from "@pos_self_order/app/components/product_box/product_box";

export class SelectProductPopup extends Component {
    static template = "pos_self_order_loyalty.SelectProductPopup";
    static props = {
        products: Set,
        getPayload: Function,
        close: Function,
    };
    static components = { ProductBox };

    confirm(product) {
        this.props.getPayload(product);
        this.props.close();
    }
}
