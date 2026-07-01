import { Component, proxy, signal, useListener, props, t } from "@odoo/owl";
import { useScrollShadow } from "../../utils/scroll_shadow_hook";
import { ProductTemplate } from "@point_of_sale/app/models/product_template";
import { ProductProduct } from "@point_of_sale/app/models/product_product";
export class ProductInfoPopup extends Component {
    static template = "pos_self_order.ProductInfoPopup";
    props = props({
        productTemplate: t.or([t.instanceOf(ProductTemplate), t.instanceOf(ProductProduct)]),
        close: t.function(),
    });

    scrollContainerRef = signal(null);

    setup() {
        this.scrollShadow = useScrollShadow(this.scrollContainerRef);
        useListener(window, "click", this.props.close);
        this.state = proxy({
            qty: 1,
        });
    }
}
