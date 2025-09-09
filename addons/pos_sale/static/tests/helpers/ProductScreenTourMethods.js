/** @odoo-module */

export function clickQuotationButton() {
    return [
        {
            content: "click quotation button",
            trigger: ".o_sale_order_button",
        },
    ];
}
export function clickSave() {
    return [
        {
            content: "Click on Save button",
            trigger: '.control-button:contains("Save")',
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
export function selectNthOrder(n, options = {}) {
    const { loadSN } = options;
    const step = [
        {
            content: `select order`,
            trigger: `.order-list .order-row:nth-child(${n})`,
        },
        {
            content: `click on select the order`,
            trigger: `.selection-item:contains('Settle the order')`,
        },
    ];
    if (loadSN) {
        step.push(...[
            {
            content: `Await confirmation demand popup`,
            trigger: `.modal-body:contains('Do you want to load the SN/Lots linked to the Sales Order?')`,
            },
            {
            content: `Choose to auto link the lot number to the order line`,
            trigger: `.button.confirm:contains('Yes')`,
            run: "click",
            },
        ]);
    }
    return step;
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

export function checkCustomerNotes(note) {
    return [
        {
            content: `check customer notes`,
            trigger: `.customer-note:contains(${note})`,
        },
    ];
}

export function checkOrdersListEmpty() {
    return [
        {
            content: "Check that the orders list is empty",
            trigger: "body:not(:has(.order-row))",
        },
    ];
}

export function downPayment20PercentFirstOrder() {
    return [
        {
            content: `select order`,
            trigger: `.order-row .col.name:first`,
        },
        {
            content: `click on select the order`,
            trigger: `.selection-item:contains('Apply a down payment (percentage)')`,
        },
        {
            content: `click on +10 button`,
            trigger: `div.numpad.row button.col:contains("+20")`,
        },
        {
            content: `click on ok button`,
            trigger: `.button.confirm`,
        },
    ];
}
