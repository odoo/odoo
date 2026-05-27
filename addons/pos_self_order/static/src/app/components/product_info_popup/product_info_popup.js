import { useRef } from "@web/owl2/utils";
import { Component, proxy, useListener } from "@odoo/owl";
import { useScrollShadow } from "../../utils/scroll_shadow_hook";
export class ProductInfoPopup extends Component {
    static template = "pos_self_order.ProductInfoPopup";
    static props = {
        productTemplate: Object,
        close: Function,
    };

    setup() {
        this.scrollShadow = useScrollShadow(useRef("scrollContainer"));
        useListener(window, "click", this.props.close);
        this.state = proxy({
            qty: 1,
        });
    }
}
