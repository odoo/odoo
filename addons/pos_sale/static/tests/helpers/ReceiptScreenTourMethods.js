//** @odoo-module */

export function checkCustomerNotes(note) {
    return [
        {
            content: `check customer notes`,
            trigger: `.customer-note:contains(${note})`,
        }
    ];
}
export function checkDownpaymentProducts(product) {
    return [
        {
            content: `check down-payment details`,
            trigger: `.orderline:contains('Down Payment') .info-list:contains(${product})`,
            run: () => {},
        }
    ];
}
