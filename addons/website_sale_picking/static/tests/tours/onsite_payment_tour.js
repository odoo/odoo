/** @odoo-module */

import tour from 'web_tour.tour'
import wTourUtils from 'website.tour_utils';
import wsTourUtils from 'website_sale.tour_utils';

tour.register('onsite_payment_tour', {
        test: true,
        url: '/web',
    },
    [
        ...wsTourUtils.addToCart({productName: 'Chair floor protection'}),
        wsTourUtils.goToCart(),
        wTourUtils.clickOnElement('Proceed to checkout', 'a:contains(Process Checkout)'),
        ...wsTourUtils.fillAdressForm(),
        wTourUtils.clickOnElement('Example shipping On Site', '.o_delivery_carrier_select:contains("Example shipping On Site")'),
        wTourUtils.clickOnElement('pay button', 'button[name="o_payment_submit_button"]:visible:not(:disabled)'),
        {
            content: "Check if the payment is successful",
            trigger: 'p:contains(Your order has been saved. Please come to the store to pay for your products)',
        },

        // Test multi products (Either physical or not)
        ...wsTourUtils.addToCart({productName: 'Customizable Desk', productHasVariants: true}),
        ...wsTourUtils.addToCart({productName: 'Warranty'}),
        wsTourUtils.goToCart({quantity: 2}),
        wTourUtils.clickOnElement('Go to payment page', 'a:contains("Process Checkout")'),
        ...wsTourUtils.fillAdressForm(),
        wTourUtils.clickOnElement('"Pay in store when picking the product"', '.o_delivery_carrier_select:contains("Example shipping On Site")'),
        wTourUtils.clickOnElement('Pay button', 'button[name="o_payment_submit_button"]:visible:not(:disabled)'),
        {
            content: "Check if the payment is successful",
            trigger: 'p:contains(Your order has been saved. Please come to the store to pay for your products)',
        },

        // Test without any physical product (option pay on site should not appear)
        ...wsTourUtils.addToCart({productName: 'Warranty'}),
        wsTourUtils.goToCart(),
        wTourUtils.clickOnElement('Go to payment page', 'a:contains("Process Checkout")'),
        ...wsTourUtils.fillAdressForm(),
        {
            content: 'Assert pay on site is NOT an option',
            trigger: 'body:not(:contains("Test Payment Provider"))',
        },
    ]
);
