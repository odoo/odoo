import { Component, useExternalListener, useState, useRef } from "@odoo/owl";
import { useScrollShadow } from "../../utils/scroll_shadow_hook";
export class ProductInfoPopup extends Component {
    static template = "pos_self_order.ProductInfoPopup";
    static props = {
        productTemplate: Object,
        close: Function,
    };

    setup() {
        this.scrollShadow = useScrollShadow(useRef("scrollContainer"));
        useExternalListener(window, "click", this.props.close);
        this.state = useState({
            qty: 1,
        });
    }
}
