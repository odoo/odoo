import { Component, proxy, signal, t, useProps } from "@odoo/owl";
import { ProductProduct } from "@point_of_sale/app/models/product_product";
import { ProductTemplate } from "@point_of_sale/app/models/product_template";
import { useScrollShadow } from "@pos_self_order/app/utils/scroll_shadow_hook";
import { useStickyTitleObserver } from "@pos_self_order/app/utils/sticky_title_observer";

export class ProductInterface extends Component {
    static template = "pos_self_order.ProductInterface";

    props = useProps({
        productTemplate: t.instanceOf(ProductTemplate),
        productVariant: t.instanceOf(ProductProduct).optional(),
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

    getImageUrl() {
        const variant = this.props.productVariant;
        if (variant) {
            return `/web/image/product.product/${variant.id}/image_512?unique=${variant.write_date}`;
        }
        const product = this.props.productTemplate;
        return `/web/image/product.template/${product.id}/image_512?unique=${product.write_date}`;
    }
}
