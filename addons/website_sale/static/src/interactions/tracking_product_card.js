import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { observeTrackingVisibility } from "@website_sale/interactions/tracking_visibility";
import wSaleUtils from "@website_sale/js/website_sale_utils";

export class ProductCardTracking extends Interaction {
    static selector =
        "article.oe_product_cart[data-product-tracking-info], div.oe_product_cart[data-product-tracking-info]";
    dynamicContent = {
        _root: { "t-on-click": this.onSelectItem },
    };

    start() {
        if (!this._getTrackingInfo()) return;
        observeTrackingVisibility(this, () => {
            const info = this._getTrackingInfo();
            if (!info) return;
            const { item_list_name, ...trackingInfo } = info;
            wSaleUtils.dispatchTrackingEvent("view_item_list_event", {
                currency: this.el.dataset.productGaCurrency,
                item_list_name,
                items: [trackingInfo],
            });
        });
    }

    _getTrackingInfo() {
        const info = JSON.parse(this.el.dataset.productTrackingInfo);
        return info.item_id || info.item_name ? info : null;
    }

    onSelectItem(event) {
        // Quick-add buttons must not also fire select_item.
        if (event.target.closest("button") || !event.target.closest("a[href]")) return;
        const info = this._getTrackingInfo();
        if (!info) return;
        const { item_list_name, ...trackingInfo } = info;
        wSaleUtils.dispatchTrackingEvent("select_item_event", {
            currency: this.el.dataset.productGaCurrency,
            item_list_name,
            trackingInfo,
        });
    }
}

registry
    .category("public.interactions")
    .add("website_sale.product_card_tracking", ProductCardTracking);
