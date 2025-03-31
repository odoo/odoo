/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('website_sale_fiscal_position_portal_tour', {
    url: '/shop?search=Super%20Product',
    steps: () => [
        {
            content: "Check price",
            trigger: ".oe_product:contains('Super product') .product_price:contains('80.00')",
        },
]});

registry.category("web_tour.tours").add('website_sale_fiscal_position_public_tour', {
    url: '/shop?search=Super%20Product',
    steps: () => [
        {
            content: "Toggle Pricelist",
            trigger: ".o_pricelist_dropdown > .dropdown-toggle",
            run: 'click',
        },
        {
            content: "Change Pricelist",
            trigger: ".dropdown-item:contains('EUROPE EUR')",
            run: 'click',
        },
        {
            content: "Check price",
            trigger: ".oe_product:contains('Super product') .product_price:contains('92.00')",
        },
]});
