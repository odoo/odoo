/** @odoo-module */

export function clickPercentTip(percent) {
    return [
        {
            trigger: `.tip-screen .percentage:contains("${percent}")`,
        },
    ];
}
export function setCustomTip(amount) {
    return [
        {
            trigger: `.tip-screen .custom-amount-form input`,
            run: `text ${amount}`,
        },
    ];
}
export function clickSettle() {
    return [
        {
            trigger: `.button.highlight.next`,
        },
    ];
}

export function isShown() {
    return [
        {
            trigger: ".pos .tip-screen",
            run: () => {},
        },
    ];
}
export function totalAmountIs(amount) {
    return [
        {
            trigger: `.tip-screen .total-amount:contains("${amount}")`,
            run: () => {},
        },
    ];
}
export function percentAmountIs(percent, amount) {
    return [
        {
            trigger: `.tip-screen .percentage:contains("${percent}") ~ .amount:contains("${amount}")`,
            run: () => {},
        },
    ];
}
export function inputAmountIs(amount) {
    return [
        {
            trigger: `.tip-screen .custom-amount-form input[data-amount="${amount}"]`,
            run: () => {},
        },
    ];
}
