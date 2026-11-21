
export function assertRewardAmounts(rewards) {
    const steps = [];
    const currencyValue = `.oe_currency_value:visible`;
    for (const [reward, amount] of Object.entries(rewards)) {
        steps.push({
            content: `check if ${reward} reward is correct`,
            trigger: `[data-reward-type=${reward}] ${currencyValue}:text(${amount})`,
        });
    }
    return steps;
}

export function submitCouponCode(code) {
    return [
        {
            content: "Enter gift card code",
            trigger: "form[name='coupon_code'] input[name='promo']",
            run: `edit ${code}`,
        },
        {
            content: "click on 'Apply'",
            trigger: 'form[name="coupon_code"] button[type="submit"]',
            run: 'click',
            expectUnloadPage: true,
        },
    ]
}

/**
 * Select the gift card payment method, apply the code and pay the amount it covers.
 *
 * @param {string} code - The code of the gift card.
 * @param {string} amount - The formatted amount the gift card is expected to pay.
 */
export function payWithGiftCard(code, amount) {
    return [
        {
            content: "Select the Gift Card payment method",
            trigger: 'input[name="o_payment_radio"][data-provider-code="gift_card"]',
            run: "click",
        },
        {
            content: "Enter the gift card code",
            trigger: 'input[name="o_loyalty_gift_card_code"]:visible',
            run: `edit ${code}`,
        },
        {
            content: "Apply the gift card",
            trigger: 'button[name="o_loyalty_gift_card_apply"]',
            run: "click",
        },
        {
            content: `Check the gift card pays ${amount}`,
            trigger: `[name="o_loyalty_payment_info"] [name="o_loyalty_amount"]:contains(${amount})`,
        },
        {
            content: "Pay with the gift card",
            trigger: `button[name="o_payment_submit_button"]:contains(${amount})`,
            run: "click",
            expectUnloadPage: true,
        },
    ];
}

/**
 * Select the eWallet payment method and pay the amount it covers.
 *
 * @param {string} amount - The formatted amount the eWallet is expected to pay.
 */
export function payWithEWallet(amount) {
    return [
        {
            content: "Select the eWallet payment method",
            trigger: 'input[name="o_payment_radio"][data-provider-code="ewallet"]',
            run: "click",
        },
        {
            content: `Check the eWallet pays ${amount}`,
            trigger: `[name="o_loyalty_payment_info"] [name="o_loyalty_amount"]:contains(${amount})`,
        },
        {
            content: "Pay with the eWallet",
            trigger: `button[name="o_payment_submit_button"]:contains(${amount})`,
            run: "click",
            expectUnloadPage: true,
        },
    ];
}
