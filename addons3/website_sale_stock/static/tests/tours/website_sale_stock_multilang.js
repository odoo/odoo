/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('website_sale_stock_multilang', {
    test: true,
    url: '/fr/shop?search=unavailable',
    steps: () => [{
        content: "Open unavailable product page",
        trigger: 'a[content="unavailable_product"]',
    }, {
        content: "Check out of stock message",
        trigger: '#out_of_stock_message:contains("Hors-stock")',
        isCheck: true,
    }, {
        content: "Check price",
        trigger: 'span:contains("123,45")',
        isCheck: true,
    }, {
        content: "Open language selector",
        trigger: '.js_language_selector button',
    }, {
        content: "Switch to English",
        trigger: '.js_change_lang[data-url_code="en"]',
    }, {
        content: "Check out of stock message",
        trigger: '#out_of_stock_message:contains("Out of stock")',
        isCheck: true,
    }, {
        content: "Check price",
        trigger: 'span:contains("123.45")',
        isCheck: true,
    }, {
        content: "Open language selector",
        trigger: '.js_language_selector button',
    }, {
        content: "Switch to French",
        trigger: '.js_change_lang[data-url_code="fr"]',
    }, {
        content: "Check out of stock message",
        trigger: '#out_of_stock_message:contains("Hors-stock")',
        isCheck: true,
    }, {
        content: "Check price",
        trigger: 'span:contains("123,45")',
        isCheck: true,
    }],
});
