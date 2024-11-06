/** @odoo-module alias=l10n_it_edi_website_sale.tour **/

import { registry } from "@web/core/registry";
import * as tourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add('shop_checkout_address', {
    url: '/shop',
    steps: () => [
        {
            content: "search Storage Box",
            trigger: 'form input[name="search"]',
            run: "edit Storage Box",
        },
        {
            content: "search Storage Box",
            trigger: 'form:has(input[name="search"]) .oe_search_button',
            run: "click",
        },
        {
            content: "select Storage Box",
            trigger: '.oe_product_cart:first a:contains("Storage Box")',
            run: "click",
        },
        {
            id: 'add_cart_step',
            content: "click on add to cart",
            trigger: '#product_detail form #add_to_cart',
            run: "click",
        },
            tourUtils.goToCart(),
        {
            content: "go to address form",
            trigger: 'a[href="/shop/checkout?try_skip_step=true"]',
            run: "click",
        },
        // check if the fields Codice Fiscale and PA index are present
        {
            content: "check if the fields Codice Destinatario is present",
            trigger: 'input[name="l10n_it_pa_index"]',
            run: "edit 1234567890123456789012345",
        },
        {
            content: "check if the fields Codice Fiscale is present",
            trigger: 'input[name="l10n_it_codice_fiscale"]',
            run: "edit 12345678901",
        },
    ]
});
