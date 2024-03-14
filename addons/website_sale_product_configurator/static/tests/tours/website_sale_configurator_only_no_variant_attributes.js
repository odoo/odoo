/** @odoo-module **/

import { registry } from "@web/core/registry";
import tourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add('tour_configurator_quick_add_only_no_variant_attributes', {
    test: true,
    url: '/shop',
    steps: () => [
        ...tourUtils.searchProduct("Short (TEST)"),
        {
            content: "open configurator",
            trigger: '.oe_product:has(a:contains("Short (TEST)")) div.o_wsale_product_btn a',
        },
        {
            content: "select M dynamic attribute",
            trigger: '.oe_advanced_configurator_modal label:contains("M never") input',
        },
        {
            content: "Go through the modal window of the product configurator",
            trigger: 'button span:contains(Continue Shopping)',
        },
        {
            content: "check that the novariants/custom attributes are displayed.",
            trigger: '.toast-body span.text-muted.small:contains("Never attribute size: M never")',
            isCheck: true,
        },
    ]
});
