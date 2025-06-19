import { registry } from "@web/core/registry";
import * as tourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add('update_billing_shipping_address', {
    url: '/shop',
    steps: () => [
        ...tourUtils.addToCart({ productName: "Office Chair Black TEST", expectUnloadPage: true }),
        tourUtils.goToCart({quantity: 1}),
        tourUtils.goToCheckout(),
        tourUtils.confirmOrder(),
        {
            content: "Edit Address",
            trigger: '#delivery_and_billing a:contains("Edit")',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Edit  billing address which is shipping address too",
            trigger: 'a.js_edit_address',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Empty the phone field",
            trigger: 'input[name="phone"]',
            run: "clear",
        },
        {
            content: "Save address",
            trigger: "a[name='website_sale_main_button']",
            run: "click",
        },
        {
            content: "Check there is a warning for required field.",
            trigger: ':invalid',
        },
    ],
});
