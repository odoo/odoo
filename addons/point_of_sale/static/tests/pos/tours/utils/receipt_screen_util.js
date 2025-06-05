import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";

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
export function totalAmountWithTipContains(value, tip, { tip15, tip20, tip25 } = {}) {
    const steps = [];

    // No tip
    if (tip === null) {
        steps.push({
            trigger: `.receipt-screen .o_payment_successful:contains("${value}")`,
        });
        steps.push({
            trigger: `.receipt-screen .o_payment_successful:not(:contains("tip"))`,
        });
        steps.push({
            trigger: `.receipt-screen .pos-receipt .order-container .orderline .product-name span:last-child`,
            run: function () {
                const productNames = document.querySelectorAll(
                    `.receipt-screen .pos-receipt .order-container .orderline .product-name span:last-child`
                );
                const noTip = Array.from(productNames).every(
                    (el) => !el.textContent.includes("Tips")
                );
                if (!noTip) {
                    throw new Error("There should be no 'Tips' in the product names.");
                }
            },
        });
    }

    // Has tip
    else {
        steps.push({
            trigger: `.receipt-screen .o_payment_successful:contains("${value} +")`,
        });
        steps.push({
            trigger: `.receipt-screen .o_payment_successful:contains("${tip} tip")`,
        });
        steps.push({
            trigger: `.receipt-screen .pos-receipt .order-container .orderline .product-name span:last-child:contains("Tips")`,
            run: function () {
                const linesDetails = document.querySelectorAll(
                    `.receipt-screen .pos-receipt .order-container .orderline .line-details`
                );
                const tipLine = Array.from(linesDetails).find((el) =>
                    el.querySelector(".product-name span:last-child").textContent.includes("Tips")
                );
                if (!tipLine) {
                    throw new Error("There should be a line with 'Tips' in the receipt.");
                }
                const tipAmount = tipLine.querySelector(".product-price").textContent;
                if (!tipAmount.includes(tip)) {
                    throw new Error(`Tip amount "${tip}" no included in "${tipAmount}".`);
                }
            },
        });
    }

    // Tip 15%
    if (tip15) {
        steps.push({
            trigger: `.receipt-screen .pos-receipt .tip-form .percentage-options .option:nth-child(1) .amount:contains("${tip15}")`,
        });
    }

    // Tip 20%
    if (tip20) {
        steps.push({
            trigger: `.receipt-screen .pos-receipt .tip-form .percentage-options .option:nth-child(2) .amount:contains("${tip20}")`,
        });
    }

    // Tip 25%
    if (tip25) {
        steps.push({
            trigger: `.receipt-screen .pos-receipt .tip-form .percentage-options .option:nth-child(3) .amount:contains("${tip25}")`,
        });
    }

    return steps;
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
export function receiptRoundingAmountIsNotThere() {
    return [
        {
            isActive: ["desktop"], // not rendered on mobile
            trigger: ".receipt-screen",
            run: function () {
                if (document.querySelector(".receipt-rounding")) {
                    throw new Error("A rounding amount has been found in receipt.");
                }
            },
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

export function discardOrderWarningDialog() {
    return [
        {
            trigger: `.modal-dialog:contains("It seems that the order has not been sent. Would you like to send it to preparation?")`,
        },
        Dialog.discard(),
    ];
}

export function confirmOrderWarningDialog() {
    return [
        {
            trigger: `.modal-dialog:contains("It seems that the order has not been sent. Would you like to send it to preparation?")`,
        },
        Dialog.confirm(),
    ];
}
