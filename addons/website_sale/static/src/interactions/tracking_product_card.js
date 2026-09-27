import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import wSaleUtils from "@website_sale/js/website_sale_utils";

export class ProductCardTracking extends Interaction {
    static selector =
        "article.oe_product_cart[data-product-tracking-info], div.oe_product_cart[data-product-tracking-info]";
    dynamicContent = {
        _root: { "t-on-click": this.onSelectItem },
    };

    onSelectItem(event) {
        // Quick-add "Add to Cart" buttons inside cards must not also fire select_item.
        if (event.target.closest("button")) return;
        const { item_list_name, ...trackingInfo } = JSON.parse(
            this.el.dataset.productTrackingInfo
        );
        wSaleUtils.dispatchTrackingEvent("select_item_event", { item_list_name, trackingInfo });
    }
}

registry
    .category("public.interactions")
    .add("website_sale.product_card_tracking", ProductCardTracking);
