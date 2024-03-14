/** @odoo-module **/

import { registry } from "@web/core/registry";
import tourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add('tour_configurator_quick_add_only_no_dynamic_attributes', {
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
            trigger: '.oe_advanced_configurator_modal label:contains("M dynamic") input',
        },
        {
            content: "Go through the modal window of the product configurator",
            extra_trigger: '.oe_advanced_configurator_modal strong:contains("Short (TEST) (M dynamic)")',
            trigger: 'button span:contains(Proceed to Checkout)',
        },
        tourUtils.assertCartContains({
            productName: 'Short (TEST) (M dynamic)',
            backend: false,
        }),
    ]
});
