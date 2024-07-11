/** @odoo-module **/

import { registry } from "@web/core/registry";
import tourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add('update_billing_shipping_address', {
    test: true,
    url: '/shop',
    steps: () => [
        ...tourUtils.addToCart({productName: "Office Chair Black TEST"}),
        tourUtils.goToCart({quantity: 1}),
        tourUtils.goToCheckout(),
        {
            content: "Edit Address",
            trigger: '#shipping_and_billing a:contains("Edit")'
        },
        {
            content: "Edit  billing address which is shipping address too",
            trigger: 'a.js_edit_address'
        },
        {
            content: "Empty the phone field",
            trigger: 'input[name="phone"]',
            run: () => {
                document.querySelector('input[name="phone"]').value = "";
            },
        },
        {
            content: "Save address",
            trigger: 'a.a-submit',
            run: "click",
        },
        {
            content: "Check there is a warning for required field.",
            trigger: 'h5.text-danger:contains("Some required fields are empty.")',
            run: () => {},
        },
    ],
});
