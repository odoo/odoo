import { registry } from '@web/core/registry';
import { clickOnElement } from '@website/js/tours/tour_utils';
import {
    addToCart,
    assertCartAmounts,
    fillAdressForm,
    goToCart,
    goToCheckout,
} from '@website_sale/js/tours/tour_utils';

registry.category('web_tour.tours').add('onsite_payment_fiscal_change_tour', {
    test: true,
    url: '/shop',
    steps: () => [
        ...addToCart({ productName: 'Super Product' }),
        goToCart(),
        goToCheckout(),
        ...fillAdressForm(),
        ...assertCartAmounts({
            taxes: '10.00',
            untaxed: '100.00',
            total: '110.00',
        }),
        clickOnElement(
            'Example shipping On Site',
            '.o_delivery_carrier_label:contains("Example shipping On Site")',
        ),
        ...assertCartAmounts({
            taxes: '5.00',
            untaxed: '100.00',
            total: '105.00',
        }),
        clickOnElement(
            '"Test Carrier"',
            '.o_delivery_carrier_label:contains("Test Carrier")',
        ),
        ...assertCartAmounts({
            taxes: '10.00',
            untaxed: '100.00',
            total: '110.00',
        }),
    ]
});
