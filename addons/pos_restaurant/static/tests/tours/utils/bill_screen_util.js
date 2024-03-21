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
