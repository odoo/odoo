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
export function emailIsSuccessful() {
    return [
        {
            trigger: `.receipt-screen .notice .text-success`,
        },
    ];
}
export function trackingMethodIsLot() {
    return [
        {
            content: `tracking method is Lot`,
            trigger: `li:contains("Lot Number")`,
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
