/** @odoo-module */

export function clickQuotationButton() {
    return [
        {
            content: "click quotation button",
            trigger: ".o_sale_order_button",
        },
    ];
}
export function selectFirstOrder() {
    return [
        {
            content: `select order`,
            trigger: `.order-row .col.name:first`,
        },
        {
            content: `click on select the order`,
            trigger: `.selection-item:contains('Settle the order')`,
        },
    ];
}
export function selectNthOrder(n) {
    return [
        {
            content: `select order`,
            trigger: `.order-list .order-row:nth-child(${n})`,
        },
        {
            content: `click on select the order`,
            trigger: `.selection-item:contains('Settle the order')`,
        },
    ];
}
export function downPaymentFirstOrder() {
    return [
        {
            content: `select order`,
            trigger: `.order-row .col.name:first`,
        },
        {
            content: `click on select the order`,
            trigger: `.selection-item:contains('Apply a down payment')`,
        },
        {
            content: `click on +10 button`,
            trigger: `div.numpad.row button.col:contains("+10")`,
        },
        {
            content: `click on ok button`,
            trigger: `.button.confirm`,
        },
    ];
}
