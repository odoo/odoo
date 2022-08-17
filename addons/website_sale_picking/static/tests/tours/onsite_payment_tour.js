/** @odoo-module */

import tour from 'web_tour.tour'

tour.register('onsite_payment_tour', {
    test: true,
    url: '/shop'
}, [ // first test : test whole onsite payment flow with physical products.
    {
        content: 'Select the first product',
        trigger: 'a:contains("Customizable Desk")',
    }, {
        content: 'Add the product to the cart',
        trigger: 'a:contains("ADD TO CART")'
    }, {
        content: 'Go to checkout page',
        trigger: 'button:contains("Proceed to Checkout")'
    }, {
        content: 'Go to payment page',
        trigger: 'a:contains("Process Checkout")'
    }, {
        content: 'Click on onsite delivery carrier',
        trigger: '.o_delivery_carrier_select:contains("On Site")'
    }, {
        content: 'Click on on site payment provider',
        trigger: '.o_payment_option_card:contains("Pay in store when picking the product")'
    }, {
        content: 'Click the pay button',
        trigger: 'button[name="o_payment_submit_button"]:visible:not(:disabled)'
    }, {
        content: 'Await the confirmation page',
        trigger: 'td:contains("Pay in store when picking the product")'
    }, {
        content: 'Head back to main page',
        trigger: '.nav-link:contains("Shop")'
    },


    { // Test multi products (Either physical or not)
        content: 'Select the first product',
        trigger: 'a:contains("Customizable Desk")',
    }, {
        content: 'Add the product to the cart',
        trigger: 'a:contains("ADD TO CART")'
    }, {
        content: 'Validate variant choice',
        trigger: 'button:contains("Continue Shopping")'
    }, {
        content: 'Head back to main page',
        trigger: '.nav-link:contains("Shop")'
    }, {
        content: 'Select the second product (Non physical)',
        trigger: 'a:contains("Warranty")',
    }, {
        content: 'Add the product to the cart',
        trigger: 'a:contains("ADD TO CART")'
    }, {
        content: 'Go to cart',
        trigger: '.nav-link[href="/shop/cart"]:contains("2")'
    }, {
        content: 'Go to payment page',
        trigger: 'a:contains("Process Checkout")'
    }, {
        content: 'Click on onsite delivery carrier',
        trigger: '.o_delivery_carrier_select:contains("On Site")'
    }, {
        content: 'Click on on site payment provider',
        trigger: '.o_payment_option_card:contains("Pay in store when picking the product")'
    }, {
        content: 'Click the pay button',
        trigger: 'button[name="o_payment_submit_button"]:visible:not(:disabled)'
    }, {
        content: 'Await the confirmation page',
        trigger: 'td:contains("Pay in store when picking the product")'
    }, {
        content: 'Head back to main page',
        trigger: '.nav-link:contains("Shop")'
    },
    // Test without any physical product (option pay on site should not appear)

    {
        content: 'Select the (Non physical) product',
        trigger: 'a:contains("Warranty")',
    }, {
        content: 'Add the product to the cart',
        trigger: 'a:contains("ADD TO CART")'
    }, {
        content: 'Go to cart',
        trigger: '.nav-link[href="/shop/cart"]:contains("1")'
    }, {
        content: 'Go to payment page',
        trigger: 'a:contains("Process Checkout")'
    }, {
        content: 'Assert pay on site is NOT an option',
        trigger: 'body:not(:contains("Pay in store when picking the product"))'
    }
]);
