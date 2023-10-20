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
