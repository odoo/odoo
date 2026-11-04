/** @odoo-module **/

import { registry } from "@web/core/registry";

function fail(errorMessage) {
    const tour = registry.get("tourManager");
    tour._consume_tour(tour.running_tour, errorMessage);
}

function assert(current, expected, info) {
    if (current !== expected) {
        fail(info + ': "' + current + '" instead of "' + expected + '".');
    }
}

registry.category("web_tour.tours").add('tour_shop_archived_variant_multi', {
    url: '/shop?search=Test Product 2',
    steps: () => [
    {
        content: "select Test Product",
        trigger: ".oe_product_cart a:text(Test Product 2)",
        run: "click",
        expectUnloadPage: true,
    },
    {
        content: 'click on the first variant',
        trigger: 'input[data-attribute_name="Size"][data-value_name="Small"]',
        run: "click",
    },
    {
        content: "click on the second variant",
        trigger: 'input[data-attribute_name="Color"][data-value_name="Black"]',
        run: "click",
    },
    {
        content: "Check that brand b is not available",
        trigger: '.css_not_available',
    },
    {
        content: "select brand b even though it's not available",
        trigger: 'input[data-attribute_name="Brand"][data-value_name="Brand B"]',
        run: "click",
    },
    {
        content: "check combination is not possible",
        trigger: '.js_main_product.css_not_available .css_not_available_msg:contains("This combination does not exist.")',
    },
    {
        content: "check add to cart not possible",
        trigger: '#add_to_cart.disabled',
    },
    {
        content: "change second variant to remove warning",
        trigger: 'input[data-attribute_name="Color"][data-value_name="White"]',
        run: "click",
    },
    {
        content: "Check that brand b is not available",
        trigger: '.css_not_available',
    },
    {
        content: "Check that second variant is disabled",
        trigger: '.css_not_available input[data-attribute_name="Color"][data-value_name="Black"]',
    },
]});

registry.category("web_tour.tours").add('test_09_pills_variant', {
    url: '/shop?search=Test Product 2',
    steps: () => [
    {
        content: "select Test Product",
        trigger: ".oe_product_cart a:text(Test Product 2)",
        run: "click",
        expectUnloadPage: true,
    },
    {
        content: "check there are two radio boxes, both hidden",
        trigger: '.js_main_product',
        run: function() {
            var buttons = [...document.querySelectorAll('input.js_variant_change')];

            function isVisuallyHidden(elem) {
                const style = window.getComputedStyle(elem);
                return style.display === "none" ||
                    style.visibility === "hidden" ||
                    style.opacity === "0" ||
                    (style.width === "0px" && style.height === "0px")
            }

            assert(buttons.length, 2, "there should be two radio inputs")
            assert(isVisuallyHidden(buttons[0]), true, "first radio input is not hidden")
            assert(isVisuallyHidden(buttons[1]), true, "second radio input is not hidden")
            assert(buttons[0].checked, true, "first radio input should be checked")
        },
    },
    {
        content: "click on the second variant label",
        trigger: 'label:contains("Small")',
        run: "click",
    },
    {
        content: 'check second variant is selected',
        trigger: 'li.o_variant_pills.active:contains("Small")',
        run: function () {
            var button = [...document.querySelectorAll('input.js_variant_change[data-attribute_name="Size"][data-value_name="Small"]')];
            assert(button.length, 1, "there should be one radio input")
            assert(button[0].checked, true, "the radio input should be checked")
        }
    },
]});
