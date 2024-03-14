/** @odoo-module **/

import { registry } from "@web/core/registry";
import tourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add('tour_configurator_quick_add_single_custom_attribute', {
    test: true,
    url: '/shop',
    steps: () => [
        ...tourUtils.searchProduct("Short (TEST)"),
        {
            content: "open configurator",
            trigger: '.oe_product:has(a:contains("Short (TEST)")) div.o_wsale_product_btn a',
        },
        {
            trigger: 'input.variant_custom_value',
            run: 'text TEST',
        },
        {
            content: "Go through the modal window of the product configurator",
            trigger: 'button span:contains(Continue Shopping)',
        },
        {
            content: "check that the novariants/custom attributes are displayed.",
            trigger: '.toast-body span.text-muted.small:contains("Always attribute size: Yes never custom: TEST")',
            isCheck: true,
        },
    ]
});
