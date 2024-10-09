/** @odoo-module */

import { registry } from "@web/core/registry";
import * as tourUtils from '@website_sale/js/tours/tour_utils';


function fail (errorMessage) {
    console.error(errorMessage);
}

registry.category("web_tour.tours").add('autocomplete_tour', {
    url: '/shop', // /shop/address is redirected if no sales order
    steps: () => [
    ...tourUtils.addToCart({productName: "A test product"}),
    tourUtils.goToCart(),
    tourUtils.goToCheckout(),
{ // Actual test
    content: 'Input in Street & Number field',
    trigger: 'input[name="street"]',
    run: "edit This is a test",
}, {
    content: 'Check if results have appeared',
    trigger: '.js_autocomplete_result',
}, {
    content: 'Input again in street field',
    trigger: 'input[name="street"]',
    run: "edit add more",
}, {
    content: 'Click on the first result',
    trigger: '.js_autocomplete_result',
    run: "click",
}, {
    content: 'Verify the autocomplete box disappeared',
    trigger: 'body:not(:has(.js_autocomplete_result))',
    run: "click",
}, { // Verify test data has been input
    content: 'Check Street & number have been set',
    trigger: 'input[name="street"]',
    run: function () {
        if (this.anchor.value !== '42 A fictional Street') {
            fail('Street value is not correct : ' + this.anchor.value)
        }
    }
}, {
    content: 'Check City is not empty anymore',
    trigger: 'input[name="city"]',
    run: function () {
        if (this.anchor.value !== 'A Fictional City') {
            fail('Street value is not correct : ' + this.anchor.value)
        }
    }
}, {
    content: 'Check Zip code is not empty anymore',
    trigger: 'input[name="zip"]',
    run: function () {
        if (this.anchor.value !== '12345') {
            fail('Street value is not correct : ' + this.anchor.value)
        }
    }
}]});
