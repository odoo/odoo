import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import * as tourUtils from "@website_sale/js/tours/tour_utils";

function patchTracking() {
    const { Tracking } = odoo.loader.modules.get("@website_sale/interactions/tracking");
    patch(Tracking.prototype, {
        onViewItem(event) {
            const productTrackingInfo = event.detail;
            document.body.setAttribute("view-event-id", productTrackingInfo.item_id);
        },
        onAddToCart(event) {
            const productsTrackingInfo = event.detail;
            document.body.setAttribute(
                "cart-event-id",
                productsTrackingInfo[0].item_id,
            );
        },
    });
}

if (odoo.loader.modules.has("@website_sale/interactions/tracking")) {
    patchTracking();
}

registry.category("web_tour.tours").add("google_analytics_view_item", {
    url: "/shop?search=Colored T-Shirt",
    steps: () => [
        {
            content: "select Colored T-Shirt",
            trigger: '.oe_product_cart a:contains("Colored T-Shirt")',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "wait until `_getCombinationInfo()` rpc is done",
            trigger: "body[view-event-id]",
            timeout: 25000,
            // Clear the attribute so that the wait further down can only be
            // satisfied by a *new* view event. Stashing the current id in a
            // module variable and interpolating it into that trigger does not
            // work: `steps()` is invoked once, eagerly, before any step runs,
            // so the template literal captures `undefined` and the trigger
            // degrades to `body[view-event-id]:not([view-event-id="undefined"])`
            // — which the id set right here already satisfies.
            run: () => {
                document.body.removeAttribute("view-event-id");
            },
        },
        {
            content: "select another variant",
            trigger:
                "ul.js_add_cart_variants ul.d-flex li:has(label.active) + li:has(label) input:not(:visible)",
            run: "click",
        },
        {
            content: "wait until `_getCombinationInfo()` rpc is done (2)",
            // The attribute was removed above, so it can only be back if a new
            // view event was generated for the variant selected in between.
            trigger: "body[view-event-id]",
            timeout: 25000,
        },
    ],
});

registry.category("web_tour.tours").add("google_analytics_add_to_cart", {
    url: "/shop?search=Basic Shirt",
    steps: () => [
        ...tourUtils.addToCart({
            productName: "Basic Shirt",
            search: false,
            expectUnloadPage: true,
        }),
        {
            trigger: "body[cart-event-id]",
        },
        {
            content: "check add to cart event",
            trigger: "a:has(.my_cart_quantity:text(1))",
            timeout: 25000,
        },
    ],
});
