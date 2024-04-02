odoo.define('l10n_it_edi_website_sale.tour', function (require) {
'use strict';

var tour = require("web_tour.tour");
const tourUtils = require('website_sale.tour_utils');

tour.register('shop_checkout_address', {
    test: true,
    url: '/shop',
},
    [
        {
            content: "search Storage Box",
            trigger: 'form input[name="search"]',
            run: "text Storage Box",
        },
        {
            content: "search Storage Box",
            trigger: 'form:has(input[name="search"]) .oe_search_button',
        },
        {
            content: "select Storage Box",
            trigger: '.oe_product_cart:first a:contains("Storage Box")',
        },
        {
            id: 'add_cart_step',
            content: "click on add to cart",
            trigger: '#product_detail form[action^="/shop/cart/update"] #add_to_cart',
        },
            tourUtils.goToCart(),
        {
            content: "go to address form",
            trigger: 'a[href="/shop/checkout?express=1"]',
        },
        // check if the fields Codice Fiscale and PA index are present
        {
            content: "check if the fields Codice Destinatario is present",
            trigger: 'input[name="l10n_it_pa_index"]',
            run: "text 1234567890123456789012345",
        },
        {
            content: "check if the fields Codice Fiscale is present",
            trigger: 'input[name="l10n_it_codice_fiscale"]',
            run: "text 12345678901",
        },
    ]
);

});
