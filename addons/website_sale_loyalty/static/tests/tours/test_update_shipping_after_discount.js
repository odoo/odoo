import { registry } from '@web/core/registry';
import {
    addToCart,
    assertCartAmounts,
    confirmOrder,
    goToCart,
    goToCheckout,
} from '@website_sale/js/tours/tour_utils';

registry.category('web_tour.tours').add('update_shipping_after_discount', {
    url: '/shop',
    checkDelay: 100,
    steps: () => [
        ...addToCart({ productName: "Plumbus" }),
        goToCart(),
        {
            content: "use eWallet to check it doesn't impact `free_over` shipping",
            trigger: 'a.btn-primary:contains(Pay with eWallet)',
            run: 'click',
        },
        goToCheckout(),
        {
            content: "select delivery1",
            trigger: 'li[name=o_delivery_method]:contains(delivery1) input',
            run: 'click',
        },
        ...assertCartAmounts({
            total: '0.00', // $100 total is covered by eWallet
            delivery: '0.00', // $100 is over $75 `free_over` amount, so free shipping
        }),
        confirmOrder(),
        {
            content: "wait for Payment page to load",
            trigger: '.o_website_sale_checkout .oe_cart:contains(Confirm order)',
        },
        {
            content: "enter discount code",
            trigger: 'form[name=coupon_code] input[name=promo]',
            run: 'edit test-50pc',
        },
        {
            content: "apply discount code",
            trigger: 'form[name=coupon_code] .a-submit',
            run: 'click',
        },
        ...assertCartAmounts({
            total: '0.00', // $50 total is covered by eWallet
            delivery: '5.00', // $50 is below $75 `free_over` amount, so no free shipping
        }),
    ],
});
