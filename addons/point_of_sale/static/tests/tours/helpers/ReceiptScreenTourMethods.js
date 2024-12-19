/** @odoo-module */

export function clickNextOrder() {
    return [
        {
            content: "go to next screen",
            trigger: ".receipt-screen .button.next.highlight[name='done']",
            mobile: false,
        },
        {
            content: "go to next screen",
            trigger: ".receipt-screen .btn-switchpane.validation-button.highlight[name='done']",
            mobile: true,
        },
    ];
}
export function clickContinueOrder() {
    return [
        {
            content: "go to next screen",
            trigger: ".receipt-screen .button.next.highlight[name='resume']",
        },
    ];
}
export function setEmail(email) {
    return [
        {
            trigger: ".receipt-screen .input-email input",
            run: `text ${email}`,
        },
    ];
}
export function clickSend(isHighlighted = true) {
    return [
        {
            trigger: `.receipt-screen .input-email .send${isHighlighted ? ".highlight" : ""}`,
        },
    ];
}
export function clickBack() {
    return [
        {
            trigger: ".receipt-screen .button.back",
        },
    ];
}

export function isShown() {
    return [
        {
            content: "receipt screen is shown",
            trigger: ".pos .receipt-screen",
            run: () => {},
        },
    ];
}
export function receiptIsThere() {
    return [
        {
            content: "there should be the receipt",
            trigger: ".receipt-screen .pos-receipt",
            run: () => {},
        },
    ];
}
export function totalAmountContains(value) {
    return [
        {
            trigger: `.receipt-screen .top-content h1:contains("${value}")`,
            run: () => {},
            mobile: false, // not rendered on mobile
        },
        {
            trigger: `.receipt-screen`,
            run: () => {},
            mobile: true, // On mobile, at least wait for the receipt screen to show
        },
    ];
}
export function emailIsSuccessful() {
    return [
        {
            trigger: `.receipt-screen .notice .successful`,
            run: () => {},
        },
    ];
}

export function nextOrder() {
    return [...isShown(), ...clickNextOrder()];
}

export function trackingMethodIsLot() {
    return [
        {
            content: `tracking method is Lot`,
            trigger: `li:contains("Lot Number")`,
            run: () => {},
        },
    ];
}

export function noDiscountAmount() {
    return [
        {
            trigger: `.pos-receipt:not(:contains("Discounts"))`,
            run: () => {},
        },
    ];
}

export function shippingDateExists() {
    return [
        {
            content: "Shipping date must be printed",
            trigger: ".pos-receipt-order-data:contains('Expected delivery:')",
        },
    ];
}
export function checkTaxDetails(tax, amount, base, total) {
    return [
        {
            trigger: `.pos-receipt-taxes span:contains('${tax}') ~ span:contains('${amount}') ~ span:contains('${base}') ~ span:contains('${total}')`,
            run: () => {},
        },
    ];
}

export function shippingDateIsToday() {
    // format the date in US, the language used by the tests
    const expectedDelivery = new Date().toLocaleDateString("en-US", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
    });

    return [
        {
            content: "Shipping date must be today",
            trigger: `.pos-receipt-order-data:contains('Expected delivery:') > div:contains('${expectedDelivery}')`,
        },
    ];
}
