import { registry } from '@web/core/registry';
import wTourUtils from '@website/js/tours/tour_utils';
import wsTourUtils from '@website_sale/js/tours/tour_utils';

registry.category('web_tour.tours').add('onsite_payment_fiscal_change_tour', {
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
            '.o_delivery_carrier_label:contains("Example shipping On Site")',
        ),
        ...wsTourUtils.assertCartAmounts({
            taxes: '5.00',
            untaxed: '100.00',
            total: '105.00',
        }),
        wTourUtils.clickOnElement(
            '"Test Carrier"',
            '.o_delivery_carrier_label:contains("Test Carrier")',
        ),
        ...wsTourUtils.assertCartAmounts({
            taxes: '10.00',
            untaxed: '100.00',
            total: '110.00',
        }),
    ]
});
