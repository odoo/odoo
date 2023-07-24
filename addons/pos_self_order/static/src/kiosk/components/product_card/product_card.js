/** @odoo-module */

import { Component } from "@odoo/owl";
import { useSelfOrderKiosk } from "@pos_self_order/kiosk/self_order_kiosk_service";
import { useService } from "@web/core/utils/hooks";

export class ProductCard extends Component {
    static template = "pos_self_order.ProductCard";
    static props = ["product"];

    setup() {
        this.selfOrderKiosk = useSelfOrderKiosk();
        this.router = useService("router");
    }

    selectProduct() {
        this.router.navigate("product", { id: this.props.product.id });
    }
}
