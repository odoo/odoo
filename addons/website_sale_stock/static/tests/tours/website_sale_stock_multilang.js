/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('website_sale_stock_multilang', {
    url: '/fr/shop?search=unavailable',
    steps: () => [{
        content: "Open unavailable product page",
        trigger: 'a[content="unavailable_product"]',
        run: "click",
    }, {
        content: "Check out of stock message",
        trigger: '#out_of_stock_message:contains("Hors-stock")',
    }, {
        content: "Check price",
        trigger: 'span:contains("123,45")',
    }, {
        content: "Open language selector",
        trigger: '.js_language_selector button',
        run: "click",
    }, {
        content: "Switch to English",
        trigger: '.js_change_lang[data-url_code="en"]',
        run: "click",
    }, {
        content: "Check out of stock message",
        trigger: '#out_of_stock_message:contains("Out of stock")',
    }, {
        content: "Check price",
        trigger: 'span:contains("123.45")',
    }, {
        content: "Open language selector",
        trigger: '.js_language_selector button',
        run: "click",
    }, {
        content: "Switch to French",
        trigger: '.js_change_lang[data-url_code="fr"]',
        run: "click",
    }, {
        content: "Check out of stock message",
        trigger: '#out_of_stock_message:contains("Hors-stock")',
    }, {
        content: "Check price",
        trigger: 'span:contains("123,45")',
    }],
});
