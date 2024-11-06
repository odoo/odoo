import { registry } from "@web/core/registry";
import {
    addToCart,
    assertCartAmounts,
    confirmOrder,
    goToCart,
    goToCheckout,
    pay,
} from '@website_sale/js/tours/tour_utils';

function assertRewardAmounts(rewards, visibleOnly) {
    const steps = [];
    const currencyValue = `.oe_currency_value${visibleOnly ? ':visible' : ':not(:visible)'}`;
    for (const [reward, amount] of Object.entries(rewards)) {
        steps.push({
            content: `check if ${reward} reward is correct`,
            trigger: `[data-reward-type=${reward}] ${currencyValue}:contains(/^${amount}$/)`,
        });
    }
    return steps;
}

function selectDelivery(provider) {
    return {
        content: `select ${provider} shipping`,
        trigger: `li[name=o_delivery_method]:contains(${provider}) input`,
        run: 'click',
    };
}

const waitForPaymentPage = {
    content: "wait for Payment page to load",
    trigger: '.o_total_card:contains(Order summary)',
};

const webTours = registry.category('web_tour.tours');

webTours.add('check_shipping_discount', {
    url: '/shop?search=Plumbus',
    checkDelay: 50,
    steps: () => [
        {
            content: "select Plumbus",
            trigger: '.oe_product a:contains("Plumbus")',
            run: "click",
        },
        {
            content: "add 3 Plumbus into cart",
            trigger: '#product_details input[name="add_qty"]',
            run: "edit 3",
        },
        {
            content: "click on 'Add to Cart' button",
            trigger: '#product_detail form #add_to_cart',
            run: "click",
        },
        goToCart({ quantity: 3 }),
        goToCheckout(),
        selectDelivery("delivery2"),
        ...assertCartAmounts({
            delivery: "10.00", // delivery2 is $10, ignoring shipping discount
            total: "304.00", // $100 per Plumbus, plus discounted delivery
        }),
        ...assertRewardAmounts({ shipping: "- 6.00" }),
        {
            content: "pay with eWallet",
            trigger: 'form[name=claim_reward] a.btn-primary:contains(Pay with eWallet)',
            run: 'click',
        },
        waitForPaymentPage,
        ...assertRewardAmounts({ discount: "- 304.00" }),
        selectDelivery("delivery1"),
        ...assertCartAmounts({ delivery: "5.00" }),
        ...assertRewardAmounts({ discount: "- 300.00", shipping: "- 5.00" }),
        {
            content: "confirm shipping method",
            trigger: '.o_total_card a[name=website_sale_main_button]',
            run: 'click',
        },
        pay(),
    ],
});

webTours.add('update_shipping_after_discount', {
    url: '/shop',
    checkDelay: 50,
    steps: () => [
        ...addToCart({ productName: "Plumbus" }),
        goToCart(),
        {
            content: "use eWallet to check it doesn't impact `free_over` shipping",
            trigger: 'a.btn-primary:contains(Pay with eWallet)',
            run: 'click',
        },
        goToCheckout(),
        selectDelivery("delivery1"),
        ...assertCartAmounts({
            total: "0.00", // $100 total is covered by eWallet
            delivery: "0.00", // $100 is over $75 `free_over` amount, so free shipping
        }),
        confirmOrder(),
        waitForPaymentPage,
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
            total: "0.00", // $50 total is covered by eWallet
            delivery: "5.00", // $50 is below $75 `free_over` amount, so no free shipping
        }),
        ...assertRewardAmounts({ discount: "- 50.00" }), // eWallet & promo code are both $50
    ],
});
