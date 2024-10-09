/** @odoo-module **/

import { registry } from "@web/core/registry";
import * as tourUtils from "@website_sale/js/tours/tour_utils";

function assertCityAndState(expectedCity, expectedState) {
    // :checked doesn't seem to work in the trigger, so let's check manually.
    let select_value = document.querySelector('select[name="city_id"]').value;
    let option = document.querySelector(`select[name="city_id"] option[value="${select_value}"]`);
    if (!option.innerText.includes(expectedCity)) {
        throw new Error("The right city was not auto-selected.");
    }

    select_value = document.querySelector('select[name="state_id"]').value;
    option = document.querySelector(`select[name="state_id"] option[value="${select_value}"]`);
    if (!option.innerText.includes(expectedState)) {
        throw new Error("The right state was not auto-selected.");
    }
}

registry.category("web_tour.tours").add("test_brazilian_address", {
    url: '/shop?search=Brazilian test product',
    steps: () => [
        ...tourUtils.addToCart({productName: "Brazilian test product", search: false}),
        tourUtils.goToCart({quantity: 1}),
        tourUtils.goToCheckout(),
        {
            content: 'base_address_extended should not be shown',
            trigger: 'select[name="city_id"]:not(:visible)',
        },
        {
            content: 'Set Brazil first',
            trigger: 'select[name="country_id"]',
            run: 'selectByLabel Brazil',
        },
        {
            content: 'base_address_extended fields should be shown',
            trigger: 'select[name="city_id"]',
        },
        {
            content: 'Input a zip second',
            trigger: 'input[name="zip"]',
            run: 'fill 12345',
        },
        {
            content: 'Check that Jacareí city and São Paulo state are automatically selected based on the previous zip',
            trigger: 'select[name="city_id"]',
            run: () => assertCityAndState('Jacareí', 'São Paulo'),
        },
        {
            content: 'Discard',
            trigger: 'a[href^="/shop/cart"]',
            run: 'click',
        },
        tourUtils.goToCheckout(),
        {
            content: 'Input a zip first',
            trigger: 'input[name="zip"]',
            run: 'fill 83490-000',
        },
        {
            content: 'Set Brazil second',
            trigger: 'select[name="country_id"]',
            run: 'selectByLabel Brazil',
        },
        {
            content: 'Check that Adrianópolis city and Paraná state are automatically selected based on the previous zip',
            trigger: 'select[name="city_id"]',
            run: () => assertCityAndState('Adrianópolis', 'Paraná'),
        },
    ],
});
