import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import * as tourUtils from "@website_sale/js/tours/tour_utils";

/**
 * Patch tracking to avoid third party calls during tests.
 */
function patchTracking() {
    const { Tracking } = odoo.loader.modules.get('@website_sale/interactions/tracking');
    patch(Tracking.prototype, {
        // Don't call super to avoid third party calls (GA).
        setup() {
            const cartTrackingEl = document.querySelector("#cart_tracking_info");
            if (cartTrackingEl?.dataset?.cartTrackingInfo) {
                document.body.setAttribute("view-cart-event", "1");
            }
            const confirmation = this.el.querySelector('div[name="order_confirmation"]');
            if (confirmation) {
                document.body.setAttribute("purchase-event", "1");
                if (sessionStorage.getItem("ga-add-payment-info-fired")) {
                    document.body.setAttribute("add-payment-info-event", "1");
                    sessionStorage.removeItem("ga-add-payment-info-fired");
                }
            }
            if (sessionStorage.getItem("ga-begin-checkout-fired")) {
                document.body.setAttribute("begin-checkout-event", "1");
                sessionStorage.removeItem("ga-begin-checkout-fired");
            }
        },
        onViewItem(event) {
            const productTrackingInfo = event.detail.trackingInfo;
            document.body.setAttribute("view-event-id", productTrackingInfo.item_id);
            document.body.setAttribute("view-event-variant", productTrackingInfo.item_variant || "");
        },
        onSelectItem(event) {
            const { trackingInfo } = event.detail;
            document.body.setAttribute("select-item-event-id", trackingInfo.item_id);
        },
        onAddToCart(event) {
            const productsTrackingInfo = event.detail;
            if (!productsTrackingInfo.items?.length) return;
            document.body.setAttribute("cart-event-id", productsTrackingInfo.items[0].item_id);
        },
        onUpdateCart(event) {
            const items = event.detail.items;
            if (!items?.length) return;
            const removedItems = items.filter(i => i.delta_quantity < 0);
            if (removedItems.length) {
                document.body.setAttribute("remove-from-cart-event-id", removedItems[0].item_id);
            }
        },
        onCheckoutStart() {
            sessionStorage.setItem("ga-begin-checkout-fired", "1");
        },
        onAddShippingInfo(event) {
            const shippingInfo = event.detail;
            if (!shippingInfo) return;
            document.body.setAttribute("shipping-tier", shippingInfo.shipping_tier);
        },
        onAddToWishlist(event) {
            const { trackingInfo } = event.detail;
            if (!trackingInfo) return;
            document.body.setAttribute("add-to-wishlist-event-id", trackingInfo.item_id);
        },
        onOrderPayment() {
            sessionStorage.setItem("ga-add-payment-info-fired", "1");
        },
    });
}

if (odoo.loader.modules.has('@website_sale/interactions/tracking')) {
    patchTracking();
} else {
    odoo.loader.bus.addEventListener('module-started', (e) => {
        if (e.detail.moduleName === '@website_sale/interactions/tracking') patchTracking();
    });
}

let itemVariant;

registry.category("web_tour.tours").add('website_sale.google_analytics_view_item', {
    steps: () => [
        ...tourUtils.goToProductPage({
            productName: "Colored T-Shirt",
            search: false,
            expectUnloadPage: true
        }),
        {
            content: "wait until `_getCombinationInfo()` rpc is done",
            trigger: 'body[view-event-id]',
            timeout: 25000,
            run: () => {
                itemVariant = document.body.getAttribute("view-event-variant");
            }
        },
        {
            content: 'select another variant',
            trigger:
                "ul.js_add_cart_variants ul.d-flex li:has(label.active) + li:has(label) input:not(:visible)",
            run: "click",
        },
        {
            content: 'wait until `_getCombinationInfo()` rpc is done (2)',
            trigger: `body[view-event-variant]:not([view-event-variant="${itemVariant}"])`,
            timeout: 25000,
        },
    ]
});

registry.category("web_tour.tours").add('website_sale.google_analytics_add_to_cart', {
    steps: () => [
        ...tourUtils.goToProductPage({
            productName: "Basic Shirt",
            search: false,
            expectUnloadPage: true
        }),
        {
            content: "Add to cart",
            trigger: '.js_product button[name="add_to_cart"]',
            run: "click",
        },
        {
            content: "verify add_to_cart event was fired",
            trigger: "body[cart-event-id]",
            timeout: 25000,
        },
    ],
});

registry.category("web_tour.tours").add("website_sale.google_analytics_select_item", {
    steps: () => [
        {
            content: "click product card to trigger select_item",
            trigger: 'article.oe_product_cart[data-product-tracking-info]',
            run: "click",
        },
        {
            content: "verify select_item event was fired",
            trigger: "body[select-item-event-id]",
            timeout: 25000,
        },
    ],
});

registry.category("web_tour.tours").add("website_sale.google_analytics_view_cart", {
    steps: () => [
        {
            content: "verify view_cart event was fired on cart page load",
            trigger: "body[view-cart-event]",
            timeout: 25000,
        },
    ],
});

registry.category("web_tour.tours").add("website_sale.google_analytics_begin_checkout", {
    steps: () => [
        {
            content: "verify begin_checkout tracking data is injected on cart page",
            trigger: "#cart_tracking_info[data-cart-tracking-info]:not(:visible)",
            timeout: 25000,
        },
        tourUtils.goToCheckout(),
        {
            content: "verify begin_checkout event was fired",
            trigger: "body[begin-checkout-event]",
            timeout: 25000,
        },
    ],
});

registry.category("web_tour.tours").add("website_sale.google_analytics_remove_from_cart", {
    steps: () => [
        {
            content: "decrease cart line quantity",
            trigger: 'button[name="minus_button"]',
            run: "click",
        },
        {
            content: "verify remove_from_cart event was fired",
            trigger: "body[remove-from-cart-event-id]",
            timeout: 25000,
        },
    ],
});

registry.category("web_tour.tours").add("website_sale.google_analytics_add_shipping_info", {
    steps: () => [
        tourUtils.goToCheckout(),
        tourUtils.selectDeliveryCarrier("Test Delivery"),
        {
            content: "verify add_shipping_info event was fired with shipping_tier",
            trigger: "body[shipping-tier]",
            timeout: 25000,
        },
    ],
});

registry.category("web_tour.tours").add("website_sale.google_analytics_add_to_wishlist", {
    steps: () => [
        ...tourUtils.goToProductPage({
            productName: "Basic Shirt",
            search: false,
            expectUnloadPage: true,
        }),
        {
            content: "wait for product tracking info to be loaded",
            trigger: "#product_detail[data-product-tracking-info]",
            timeout: 25000,
        },
        {
            content: "click add to wishlist",
            trigger: "#product_detail .o_add_wishlist_dyn:not([disabled])",
            run: "click",
        },
        {
            content: "verify add_to_wishlist event was fired",
            trigger: "body[add-to-wishlist-event-id]",
            timeout: 25000,
        },
    ],
});

registry.category("web_tour.tours").add("website_sale.google_analytics_purchase", {
    steps: () => [
        tourUtils.goToCheckout(),
        tourUtils.selectDeliveryCarrier("Test Delivery"),
        tourUtils.confirmOrder(),
        {
            content: "select wire transfer payment",
            trigger: 'input[name="o_payment_radio"][data-payment-method-code="wire_transfer"]',
            run: "click",
        },
        {
            trigger: 'input[name="o_payment_radio"][data-payment-method-code="wire_transfer"]:checked',
        },
        ...tourUtils.pay({ expectUnloadPage: true }),
        {
            content: "verify purchase and add_payment_info events were fired on confirmation page",
            trigger: "body[purchase-event][add-payment-info-event]",
            timeout: 30000,
        },
    ],
});
