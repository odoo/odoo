import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class ProductCardTracking extends Interaction {
    static selector =
        "article.oe_product_cart[data-product-tracking-info], div.oe_product_cart[data-product-tracking-info]";
    dynamicContent = {
        _root: { "t-on-click": this.onSelectItem },
    };

    onSelectItem(event) {
        if (event.target.closest("button")) return;
        const { item_list_name, ...trackingInfo } = JSON.parse(
            this.el.dataset.productTrackingInfo
        );
        document.querySelector(".oe_website_sale")?.dispatchEvent(
            new CustomEvent("select_item_event", {
                detail: { item_list_name, trackingInfo },
            })
        );
    }
}

registry.category("public.interactions").add("website_sale.product_card_tracking", ProductCardTracking);
