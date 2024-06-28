/** @odoo-module */

import { registry } from "@web/core/registry";
import wTourUtils from '@website/js/tours/tour_utils';
import wsTourUtils from '@website_sale/js/tours/tour_utils';

registry.category("web_tour.tours").add('onsite_payment_tour', {
        test: true,
        url: '/web',
        steps: () => [
        ...wsTourUtils.addToCart({productName: 'Chair floor protection'}),
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
        ...wsTourUtils.addToCart({productName: 'Customizable Desk', productHasVariants: true}),
        ...wsTourUtils.addToCart({productName: 'Warranty'}),
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
        ...wsTourUtils.addToCart({productName: 'Warranty'}),
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

registry.category("web_tour.tours").add('onsite_payment_fiscal_change_tour', {
    test: true,
    url: '/shop',
    steps: () => [
        ...wsTourUtils.addToCart({ productName: 'Super Product' }),
        wsTourUtils.goToCart(),
        wsTourUtils.goToCheckout(),
        ...wsTourUtils.fillAdressForm(),
        ...wsTourUtils.assertCartAmounts({
            taxes: '10.00',
            untaxed: '100.00',
            total: '110.00',
        }),
        wTourUtils.clickOnElement(
            'Example shipping On Site',
            '.o_delivery_carrier_select:contains("Example shipping On Site")',
        ),
        ...wsTourUtils.assertCartAmounts({
            taxes: '5.00',
            untaxed: '100.00',
            total: '105.00',
        }),
        wTourUtils.clickOnElement(
            '"Standard delivery"',
            '.o_delivery_carrier_select:contains("Standard delivery")',
        ),
        ...wsTourUtils.assertCartAmounts({
            taxes: '10.00',
            untaxed: '100.00',
            total: '110.00',
        }),
    ]
});
