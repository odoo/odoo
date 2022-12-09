/** @odoo-module */

import { createTourMethods } from "@point_of_sale/../tests/tours/helpers/utils";

class Do {
    clickPercentTip(percent) {
        return [
            {
                trigger: `.tip-screen .percentage:contains("${percent}")`,
            },
        ];
    }
    setCustomTip(amount) {
        return [
            {
                trigger: `.tip-screen .custom-amount-form input`,
                run: `text ${amount}`,
            },
        ];
    }
}

class Check {
    isShown() {
        return [
            {
                trigger: ".pos .tip-screen",
                run: () => {},
            },
        ];
    }
    totalAmountIs(amount) {
        return [
            {
                trigger: `.tip-screen .total-amount:contains("${amount}")`,
                run: () => {},
            },
        ];
    }
    percentAmountIs(percent, amount) {
        return [
            {
                trigger: `.tip-screen .percentage:contains("${percent}") ~ .amount:contains("${amount}")`,
                run: () => {},
            },
        ];
    }
    inputAmountIs(amount) {
        return [
            {
                trigger: `.tip-screen .custom-amount-form input[data-amount="${amount}"]`,
                run: () => {},
            },
        ];
    }
}

// FIXME: this is a horrible hack to export an object as named exports.
// eslint-disable-next-line no-undef
Object.assign(__exports, createTourMethods("TipScreen", Do, Check));
