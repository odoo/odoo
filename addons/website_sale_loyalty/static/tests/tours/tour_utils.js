export function assertRewardAmounts(rewards) {
    const steps = [];
    for (const [reward, amount] of Object.entries(rewards)) {
        steps.push({
            content: `check if ${reward} reward is correct`,
            trigger: `span.o_reward_${reward}:text($ ${amount})`,
        });
    }
    return steps;
}

export function submitCouponCode(code) {
    return [
        {
            content: "Enter gift card code",
            trigger: "input[name='promo']",
            run: `edit ${code}`,
        },
        {
            content: "click on 'Apply'",
            trigger: 'button[name="apply_promo"]',
            run: "click",
        },
    ]
}
