/** @odoo-module */

import { registry } from "@web/core/registry";
import wTourUtils from '@website/js/tours/tour_utils';
import wsTourUtils from '@website_sale/js/tours/tour_utils';

registry.category("web_tour.tours").add('onsite_payment_tour', {
        test: true,
        url: '/shop',
        steps: () => [
        ...wsTourUtils.addToCart({productName: 'Test Product'}),
        wsTourUtils.goToCart(),
        wsTourUtils.goToCheckout(),
        ...wsTourUtils.fillAdressForm(),
        wTourUtils.clickOnElement('Example shipping On Site', '.o_delivery_carrier_select:contains("Example shipping On Site")'),
        wTourUtils.clickOnElement(
            '"Pay on site"',
            'input[name="o_payment_radio"][data-payment-method-code="pay_on_site"]',
        ),
        wsTourUtils.pay(),
        {
            content: "Check if the payment is successful",
            trigger: 'p:contains(Your order has been saved. Please come to the store to pay for your products)',
        },

        // Test multi products (Either physical or not)
        ...wsTourUtils.addToCart({productName: 'Test Product'}),
        ...wsTourUtils.addToCart({productName: 'Test Service Product'}),
        wsTourUtils.goToCart({quantity: 2}),
        wsTourUtils.goToCheckout(),
        ...wsTourUtils.fillAdressForm(),
        wTourUtils.clickOnElement('"Pay in Store"', '.o_delivery_carrier_select:contains("Example shipping On Site")'),
        wTourUtils.clickOnElement(
            '"Pay on site"',
            'input[name="o_payment_radio"][data-payment-method-code="pay_on_site"]',
        ),
        wsTourUtils.pay(),
        {
            content: "Check if the payment is successful",
            trigger: 'p:contains(Your order has been saved. Please come to the store to pay for your products)',
        },

        // Test without any physical product (option pay on site should not appear)
        ...wsTourUtils.addToCart({productName: 'Test Service Product'}),
        wsTourUtils.goToCart(),
        wsTourUtils.goToCheckout(),
        ...wsTourUtils.fillAdressForm(),
        {
            content: 'Assert there is no carrier choice since the order only contains services',
            trigger: 'body:not(.o_delivery_carrier_select)',
            extra_trigger: '#address_on_payment',
            isCheck: true,
        },
        {
            content: 'Assert pay on site is NOT a payment option',
            trigger: 'body:not(:contains("Pay on site"))',
            isCheck: true,
        },
    ]
});
