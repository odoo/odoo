/** @odoo-module */

export function clickOk() {
    return [
        {
            content: `go back`,
            trigger: `.receipt-screen .button.next`,
        },
    ];
}

export function isShown() {
    return [
        {
            content: "Bill screen is shown",
            trigger: '.receipt-screen h2:contains("Bill Printing")',
            run: () => {},
        },
    ];
}

export function clickBillButton() {
    return [
        {
            content: "click review button",
            trigger: ".btn-switchpane.review-button",
            mobile: true,
        },
        {
            content: "click more button",
            trigger: ".mobile-more-button",
            mobile: true,
        },
        {
            content: "click bill button",
            trigger: '.control-button:contains("Bill")',
        },
    ];
}

export function isQRCodeShown() {
    return [
        {
            content: "QR codes are shown",
            trigger: '#posqrcode',
            run: () => {},
        },
    ];
}
