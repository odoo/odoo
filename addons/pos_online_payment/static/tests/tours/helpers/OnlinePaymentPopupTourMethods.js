/** @odoo-module */

export function amountIs(amount) {
    return {
        content: `displayed amount is ${amount}`,
        trigger: `.amount:contains("${amount}")`,
        isCheck: true,
        is_modal: true,
    };
}
