/** @odoo-module **/

import { registry } from "@web/core/registry";
import configuratorTourUtils from "@sale/js/tours/product_configurator_tour_utils";

registry.category("web_tour.tours").add('website_sale_product_configurator_optional_products_tour', {
    steps: () => [
        {
            trigger: 'ul.js_add_cart_variants span:contains("Aluminium") ~ span.badge:contains("50.40")',
        },
        {
    content: 'Click Aluminium Option',
    trigger: 'ul.js_add_cart_variants span:contains("Aluminium")',
    run: "click",
}, {
    content: 'Add to cart',
    trigger: '#add_to_cart',
    run: "click",
},
configuratorTourUtils.assertPriceTotal("800.40"),
]});
