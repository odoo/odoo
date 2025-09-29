
export function assertRewardAmounts(rewards) {
    const steps = [];
    const currencyValue = `.oe_currency_value:visible`;
    for (const [reward, amount] of Object.entries(rewards)) {
        steps.push({
            content: `check if ${reward} reward is correct`,
            trigger: `[data-reward-type=${reward}] ${currencyValue}:contains(/^${amount}$/)`,
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