export function clickPercentTip(percent) {
    return [
        {
            trigger: `.tip-screen .percentage:contains("${percent}")`,
            run: "click",
        },
    ];
}
export function clickNoTip() {
    return [
        {
            trigger: `.tip-screen .no-tip button`,
            run: "click",
        },
    ];
}
export function setCustomTip(amount) {
    return [
        {
            trigger: `.tip-screen .custom-amount-form input`,
            run: `edit ${amount}`,
        },
    ];
}
export function clickSettle() {
    return [
        {
            trigger: `.button.highlight.next`,
            run: "click",
        },
    ];
}

export function isShown() {
    return [
        {
            trigger: ".pos .tip-screen",
        },
    ];
}
export function totalAmountIs(amount) {
    return [
        {
            trigger: `.tip-screen .total-amount:contains("${amount}")`,
        },
    ];
}
export function percentAmountIs(percent, amount) {
    return [
        {
            trigger: `.tip-screen .percentage:contains("${percent}") ~ .amount:contains("${amount}")`,
        },
    ];
}
export function inputAmountIs(amount) {
    return [
        {
            trigger: `.tip-screen .custom-amount-form input[data-amount="${amount}"]`,
        },
    ];
}
