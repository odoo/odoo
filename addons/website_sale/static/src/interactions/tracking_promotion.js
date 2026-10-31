import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { observeTrackingVisibility } from "@website_sale/interactions/tracking_visibility";
import wSaleUtils from "@website_sale/js/website_sale_utils";

export class PromotionTracking extends Interaction {
    static selector = "[data-promotion-tracking-info]";
    dynamicContent = {
        _root: {
            "t-on-submit": this.onSelectPromotion,
            "t-on-click": this.onPromotionClick,
        },
    };

    start() {
        const info = this._getTrackingInfo();
        if (!info) return;
        observeTrackingVisibility(this, () => {
            wSaleUtils.dispatchTrackingEvent("view_promotion_event", info);
        });
    }

    _getTrackingInfo(productId) {
        const { product_items: productItems, ...info } = JSON.parse(
            this.el.dataset.promotionTrackingInfo
        );
        if (productId && productItems) {
            info.items = productItems[productId] ? [productItems[productId]] : [];
        }
        return (info.promotion_id || info.promotion_name) && info.items?.length ? info : null;
    }

    onPromotionClick(event) {
        // Forms are measured on submit, so their submit button must not count twice.
        if (this.el.matches("form") || !event.target.closest("a[href], button")) return;
        this.onSelectPromotion();
    }

    onSelectPromotion() {
        const productId = this.el.querySelector('select[name="product_id"]')?.value;
        const info = this._getTrackingInfo(productId);
        if (info) wSaleUtils.dispatchTrackingEvent("select_promotion_event", info);
    }
}

registry.category("public.interactions").add("website_sale.promotion_tracking", PromotionTracking);
