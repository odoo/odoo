/** @odoo-module */

import tour from 'web_tour.tour';
import tourUtils from 'website_sale.tour_utils';


function fail (errorMessage) {
    tour._consume_tour(tour.running_tour, errorMessage);
}

tour.register('autocomplete_tour', {
    test: true,
    url: '/shop', // /shop/address is redirected if no sales order
}, [{
    content: "search test product",
    trigger: 'form input[name="search"]',
    run: "text A test product",
},{
    content: 'Go to the product page',
    trigger: '.dropdown-item:contains("A test product")'
}, {
    content: 'Add to cart',
    trigger: '#add_to_cart'
},
    tourUtils.goToCart(),
{
    content: 'Go to process checkout',
    trigger: 'a:contains("Process Checkout")'
}, { // Actual test
    content: 'Input in Street & Number field',
    trigger: 'input[name="street"]',
    run: 'text This is a test'
}, {
    content: 'Check if results have appeared',
    trigger: '.js_autocomplete_result',
    run: function () {}
}, {
    content: 'Input again in street field',
    trigger: 'input[name="street"]',
    run: 'text add more'
}, {
    content: 'Click on the first result',
    trigger: '.js_autocomplete_result'
}, {
    content: 'Verify the autocomplete box disappeared',
    trigger: 'body:not(:has(.js_autocomplete_result))'
}, { // Verify test data has been input
    content: 'Check Street & number have been set',
    trigger: 'input[name="street"]',
    run: function () {
        if (this.$anchor.val() !== '42 A fictional Street') {
            fail('Street value is not correct : ' + this.$anchor.val())
        }
    }
}, {
    content: 'Check City is not empty anymore',
    trigger: 'input[name="city"]',
    run: function () {
        if (this.$anchor.val() !== 'A Fictional City') {
            fail('Street value is not correct : ' + this.$anchor.val())
        }
    }
}, {
    content: 'Check Zip code is not empty anymore',
    trigger: 'input[name="zip"]',
    run: function () {
        if (this.$anchor.val() !== '12345') {
            fail('Street value is not correct : ' + this.$anchor.val())
        }
    }
}]);
