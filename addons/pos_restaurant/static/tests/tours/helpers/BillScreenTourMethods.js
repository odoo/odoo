/** @odoo-module */

export function closeBillPopup() {
    return [
        {
            content: `Close bill popup`,
            trigger: `.btn-close`,
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

export function isQRCodeShown() {
    return [
        {
            content: "QR codes are shown",
            trigger: "#posqrcode",
            run: () => {},
        },
    ];
}
