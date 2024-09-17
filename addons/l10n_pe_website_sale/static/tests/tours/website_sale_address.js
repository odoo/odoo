/** @odoo-module **/

import { registry } from "@web/core/registry";
import tourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add('update_the_address_for_peru_company', {
    test: true,
    url: '/shop',
    steps: () => [
        ...tourUtils.addToCart({ productName: "Test Product" }),
        tourUtils.goToCart({ quantity: 1 }),
        {
            content: "Go to checkout",
            trigger: "a:contains('Checkout')",
            run: "click",
        },
        {
            content: "Fill vat",
            trigger: 'input[name="vat"]',
            run: "text 111111111111",
        },
        {
            content: "Fill city",
            trigger: 'input[name="city"]',
            run: "text Scranton",
        },
        {
            content: "Save address",
            trigger: 'a:contains("Save address")',
            run: "click",
        },
        {
            content: "Add new billing address",
            trigger: '.all_billing a[href^="/shop/address?mode=billing"]:contains("Add address")',
            run: "click",
        },
        ...tourUtils.fillAdressForm(),
        ...tourUtils.payWithTransfer(),
    ],
});
