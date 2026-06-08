import { useExternalListener, useRef } from "@web/owl2/utils";
import { Component, proxy, props, types } from "@odoo/owl";
import { useScrollShadow } from "../../utils/scroll_shadow_hook";
export class ProductInfoPopup extends Component {
    static template = "pos_self_order.ProductInfoPopup";
    props = props({
        productTemplate: types.object(),
        close: types.function(),
    });

    setup() {
        this.scrollShadow = useScrollShadow(useRef("scrollContainer"));
        useExternalListener(window, "click", this.props.close);
        this.state = proxy({
            qty: 1,
        });
    }
}
