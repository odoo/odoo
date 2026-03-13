import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

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
        },
        onViewItem(event) {
            const productTrackingInfo = event.detail.trackingInfo;
            document.body.setAttribute("view-event-id", productTrackingInfo.item_id);
        },
        onSelectItem(event) {
            const { trackingInfo } = event.detail;
            document.body.setAttribute("select-item-event-id", trackingInfo.item_id);
        },
        onAddToCart(event) {
            const productsTrackingInfo = event.detail;
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
            document.body.setAttribute("begin-checkout-event", "1");
        },
        onAddShippingInfo(event) {
            const shippingInfo = event.detail;
            if (!shippingInfo) return;
            document.body.setAttribute("shipping-tier", shippingInfo.shipping_tier);
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

let itemId;


registry.category("web_tour.tours").add('website_sale.google_analytics_view_item', {
    steps: () => [
        {
            content: "select Colored T-Shirt",
            trigger: '.oe_product_cart a:contains("Colored T-Shirt")',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "wait until `_getCombinationInfo()` rpc is done",
            trigger: 'body[view-event-id]',
            timeout: 25000,
            run: () => {
                itemId = document.body.getAttribute("view-event-id");
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
            // a new view event should have been generated, for another variant
            trigger: `body[view-event-id]:not([view-event-id="${itemId}"])`,
            timeout: 25000,
        },
    ]
});

registry.category("web_tour.tours").add('website_sale.google_analytics_add_to_cart', {
    steps: () => [
        {
            content: "go to Basic Shirt product page",
            trigger: '.oe_product_cart a:contains("Basic Shirt")',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "add to cart",
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
        {
            content: "click checkout to trigger begin_checkout event",
            trigger: 'a[name="website_sale_main_button"]',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "verify we reached checkout page",
            trigger: ".o_website_sale_checkout",
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
        {
            content: "proceed to checkout",
            trigger: 'a[name="website_sale_main_button"]',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "select delivery method",
            trigger: 'input[name="o_delivery_radio"]',
            run: "click",
        },
        {
            content: "verify add_shipping_info event was fired with shipping_tier",
            trigger: "body[shipping-tier]",
            timeout: 25000,
        },
    ],
});
