import { Component } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { ProductNameWidget } from "@pos_self_order/app/components/product_name_widget/product_name_widget";

export class ProductCard extends Component {
    static template = "pos_self_order.ProductCard";
    static props = ["product", "onClick", "qty?"];
    static components = { ProductNameWidget };

    setup() {
        this.selfOrder = useSelfOrder();
    }

    onClickProduct(target) {
        this.props.onClick(this.props.product, target);
    }
}
