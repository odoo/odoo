/** @odoo-module **/

import tour from 'web_tour.tour';

tour.register('website_sale_stock_multilang', {
    test: true,
    url: '/fr/shop?search=unavailable',
},
[{
    content: "Open unavailable product page",
    trigger: 'a[content="unavailable_product"]',
}, {
    content: "Check out of stock message",
    trigger: '#out_of_stock_message:contains("Hors-stock")',
    run: () => {}, // This is a check.
}, {
    content: "Check price",
    trigger: 'span:contains("123,45")',
    run: () => {}, // This is a check.
}, {
    content: "Open language selector",
    trigger: '.js_language_selector button',
}, {
    content: "Switch to English",
    trigger: '.js_change_lang[data-url_code="en"]',
}, {
    content: "Check out of stock message",
    trigger: '#out_of_stock_message:contains("Out of stock")',
    run: () => {}, // This is a check.
}, {
    content: "Check price",
    trigger: 'span:contains("123.45")',
    run: () => {}, // This is a check.
}, {
    content: "Open language selector",
    trigger: '.js_language_selector button',
}, {
    content: "Switch to French",
    trigger: '.js_change_lang[data-url_code="fr"]',
}, {
    content: "Check out of stock message",
    trigger: '#out_of_stock_message:contains("Hors-stock")',
    run: () => {}, // This is a check.
}, {
    content: "Check price",
    trigger: 'span:contains("123,45")',
    run: () => {}, // This is a check.
}]);
