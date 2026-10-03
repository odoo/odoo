import { Component, useProps, t } from "@odoo/owl";
import { ProductCard } from "@pos_self_order/app/components/product_card/product_card";

export class SelectProductPopup extends Component {
    static template = "pos_self_order_loyalty.SelectProductPopup";
    static components = { ProductCard };

    setup() {
        this.props = useProps({
            products: t.object(),
            getPayload: t.function(),
            close: t.function(),
        });
    }

    confirm(product) {
        this.props.getPayload(product);
        this.props.close();
    }
}
