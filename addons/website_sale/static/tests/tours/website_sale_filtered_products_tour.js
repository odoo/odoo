/** @odoo-module **/

import tour from 'web_tour.tour';

function fail(errorMessage) {
    tour._consume_tour(tour.running_tour, errorMessage);
}

function assert(current, expected, info) {
    if (current !== expected) {
        fail(info + ': "' + current + '" instead of "' + expected + '".');
    }
}

tour.register('website_sale.filtered_products_tour', {
    test: true,
    url: '/shop?attrib=1-2&attrib=',
}, [
    {
        content: "Open product page",
        trigger: '.oe_product_cart a:contains("Conference Chair")',
    },
    {
        content: 'check variant is selected',
        trigger: 'input.js_variant_change[data-attribute_name="Legs"][data-value_name="Aluminium"]',
        run: function () {
            var button = $('input.js_variant_change[data-attribute_name="Legs"][data-value_name="Aluminium"]');
            assert(button[0].checked, true, "the radio input should be checked")
        },
    },
    {
        content: "Return to shop",
        trigger: 'a:contains("All Products")',
    },
    {
        content: 'Check filter is selected',
        trigger: '.form-check-input:checked+label:contains("Aluminium")',
        run: function () {
            var labels = $('.form-check-input:checked+label:contains("Aluminium")');
            assert(labels.html(), "Aluminium", "the radio input should be checked")
        },
    },
]);
