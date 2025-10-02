export function clickNextOrder() {
    return [
        {
            isActive: ["desktop"],
            content: "go to next screen",
            trigger: ".receipt-screen .button.next.highlight[name='done']",
            run: "click",
        },
        {
            isActive: ["mobile"],
            content: "go to next screen",
            trigger: ".receipt-screen .btn-switchpane.validation-button.highlight[name='done']",
            run: "click",
        },
    ];
}
export function clickContinueOrder() {
    return [
        {
            content: "go to next screen",
            trigger: ".receipt-screen .button.next.highlight[name='resume']",
            run: "click",
        },
    ];
}
export function setEmail(email) {
    return [
        {
            trigger: ".receipt-screen .send-receipt-email-input",
            run: `edit ${email}`,
        },
    ];
}
export function clickSend() {
    return [
        {
            run: "click",
            trigger: `.receipt-screen button i.fa-paper-plane`,
        },
    ];
}
export function clickBack() {
    return [
        {
            trigger: ".receipt-screen .button.back",
            run: "click",
        },
    ];
}

export function isShown() {
    return [
        {
            content: "receipt screen is shown",
            trigger: ".pos .receipt-screen",
        },
    ];
}
export function receiptIsThere() {
    return [
        {
            content: "there should be the receipt",
            trigger: ".receipt-screen .pos-receipt",
        },
    ];
}
export function totalAmountContains(value) {
    return [
        {
            isActive: ["desktop"], // not rendered on mobile
            trigger: `.receipt-screen .o_payment_successful:contains("${value}")`,
        },
        {
            isActive: ["mobile"], // On mobile, at least wait for the receipt screen to show
            trigger: `.receipt-screen`,
        },
    ];
}
export function receiptAmountTotalIs(value) {
    return [
        {
            isActive: ["desktop"], // not rendered on mobile
            trigger: `.receipt-screen .receipt-total:contains("${value}")`,
        },
        {
            isActive: ["mobile"], // On mobile, at least wait for the receipt screen to show
            trigger: `.receipt-screen`,
        },
    ];
}
export function receiptRoundingAmountIs(value) {
    return [
        {
            isActive: ["desktop"], // not rendered on mobile
            trigger: `.receipt-screen .receipt-rounding:contains("${value}")`,
        },
    ];
}
export function paymentLineContains(paymentMethodName, amount) {
    return [
        {
            content: `Check if payment line contains ${paymentMethodName} with amount ${amount}`,
            trigger: `.receipt-screen .paymentlines:contains("${paymentMethodName}"):has(.pos-receipt-right-align:contains("${amount}"))`,
        },
    ];
}
export function receiptToPayAmountIs(value) {
    return [
        {
            isActive: ["desktop"], // not rendered on mobile
            trigger: `.receipt-screen .receipt-to-pay:contains("${value}")`,
        },
    ];
}
export function receiptToPayAmountIsNotThere() {
    return [
        {
            isActive: ["desktop"], // not rendered on mobile
            trigger: ".receipt-screen",
            run: function () {
                if (document.querySelector(".receipt-to-pay")) {
                    throw new Error("An amount to pay has been found in receipt.");
                }
            },
        },
    ];
}
export function receiptChangeAmountIs(value) {
    return [
        {
            isActive: ["desktop"], // not rendered on mobile
            trigger: `.receipt-screen .receipt-change:contains("${value}")`,
        },
    ];
}
export function receiptChangeAmountIsNotThere() {
    return [
        {
            isActive: ["desktop"], // not rendered on mobile
            trigger: ".receipt-screen",
            run: function () {
                if (document.querySelector(".receipt-change")) {
                    throw new Error("An change amount has been found in receipt.");
                }
            },
        },
    ];
}
export function emailIsSuccessful() {
    return [
        {
            trigger: `.receipt-screen .notice .text-success`,
        },
    ];
}
export function trackingMethodIsLot(lot) {
    return [
        {
            content: `tracking method is Lot`,
            trigger: `li.lot-number:contains("Lot Number ${lot}")`,
            run: function () {
                if (document.querySelectorAll("li.lot-number").length !== 1) {
                    throw new Error(`Expected exactly one 'Lot Number ${lot}' element.`);
                }
            },
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
            run: "click",
        },
    ];
}

export function shippingDateIsToday() {
    // format the date in US, the language used by the tests
    const expectedDelivery = new Date().toLocaleString("en-US", luxon.DateTime.DATE_SHORT);

    return [
        {
            content: "Shipping date must be today",
            trigger: `.pos-receipt-order-data:contains('Expected delivery:') > div:contains('${expectedDelivery}')`,
        },
    ];
}

export function cashierNameExists(name) {
    return [
        {
            content: `Cashier ${name} exists on the receipt`,
            trigger: `.pos-receipt-contact .cashier:contains(Served by):contains(${name})`,
        },
    ];
}

export function containsOrderLine(name, quantity, price_unit, line_price) {
    return [
        {
            content: `Order line with name: ${name}, quantity: ${quantity}, price per unit: ${price_unit}, and line price: ${line_price} exists`,
            trigger: `.pos-receipt .orderline:has(.product-name:contains('${name}')):has(.qty:contains('${quantity}')):has(.product-price:contains('${line_price}')):has(.price-per-unit:contains('${price_unit}'))`,
        },
    ];
}
