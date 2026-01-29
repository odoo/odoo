/** @odoo-module */

import { registry } from "@web/core/registry";
import wTourUtils from '@website/js/tours/tour_utils';
import wsTourUtils from '@website_sale/js/tours/tour_utils';

registry.category("web_tour.tours").add('onsite_payment_tour', {
        test: true,
        url: '/web',
        steps: () => [
        ...wsTourUtils.addToCart({productName: 'Product Consumable'}),
        wsTourUtils.goToCart(),
        wsTourUtils.goToCheckout(),
        ...wsTourUtils.fillAdressForm(),
        wTourUtils.clickOnElement('Example shipping On Site', '.o_delivery_carrier_select:contains("Example shipping On Site")'),
        wTourUtils.clickOnElement(
            '"Pay on site"',
            'input[name="o_payment_radio"][data-payment-method-code="pay_on_site"]',
        ),
        wTourUtils.clickOnElement('pay button', 'button[name="o_payment_submit_button"]:visible:not(:disabled)'),
        {
            content: "Check if the payment is successful",
            trigger: 'p:contains(Your order has been saved. Please come to the store to pay for your products)',
        },

        // Test multi products (Either physical or not)
        ...wsTourUtils.addToCart({productName: 'Product Consumable'}),
        ...wsTourUtils.addToCart({productName: 'Product Service'}),
        wsTourUtils.goToCart({quantity: 2}),
        wsTourUtils.goToCheckout(),
        ...wsTourUtils.fillAdressForm(),
        wTourUtils.clickOnElement('"Pay in Store"', '.o_delivery_carrier_select:contains("Example shipping On Site")'),
        wTourUtils.clickOnElement(
            '"Pay on site"',
            'input[name="o_payment_radio"][data-payment-method-code="pay_on_site"]',
        ),
        wTourUtils.clickOnElement('Pay button', 'button[name="o_payment_submit_button"]:visible:not(:disabled)'),
        {
            content: "Check if the payment is successful",
            trigger: 'p:contains(Your order has been saved. Please come to the store to pay for your products)',
        },

        // Test without any physical product (option pay on site should not appear)
        ...wsTourUtils.addToCart({productName: 'Product Service'}),
        wsTourUtils.goToCart(),
        wsTourUtils.goToCheckout(),
        ...wsTourUtils.fillAdressForm(),
        {
            content: 'Assert pay on site is NOT an option',
            trigger: 'body:not(:contains("Test Payment Provider"))',
            isCheck: true,
        },
    ]
});
