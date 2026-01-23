import { Component } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { ProductNameWidget } from "../product_name_widget/product_name_widget";

export class ProductBox extends Component {
    static template = "pos_self_order.ProductBox";
    static props = {
        product: Object,
        onClick: Function,
        bigList: Boolean,
        qty: { type: Number, optional: true },
        free: { type: Boolean, optional: true },
    };
    static defaultProps = {
        qty: false,
        free: false,
    };
    static components = { ProductNameWidget };

    setup() {
        this.selfOrder = useSelfOrder();
    }

    get product() {
        return this.props.product;
    }
}
