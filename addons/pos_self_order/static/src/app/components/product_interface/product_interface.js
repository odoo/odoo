import { Component, props, proxy, signal, t } from "@odoo/owl";
import { ProductTemplate } from "@point_of_sale/app/models/product_template";
import { useScrollShadow } from "@pos_self_order/app/utils/scroll_shadow_hook";
import { useStickyTitleObserver } from "@pos_self_order/app/utils/sticky_title_observer";

export class ProductInterface extends Component {
    static template = "pos_self_order.ProductInterface";

    props = props({
        productTemplate: t.instanceOf(ProductTemplate),
        goBack: t.function().optional(() => {}),
        class: t.string().optional(),
    });

    scrollContainerRef = signal(null);
    setup() {
        this.state = proxy({
            showStickyTitle: false,
        });
        this.scrollShadow = useScrollShadow(this.scrollContainerRef);
        this.productNameRef = useStickyTitleObserver(
            (isSticky) => (this.state.showStickyTitle = isSticky)
        );
    }
}
