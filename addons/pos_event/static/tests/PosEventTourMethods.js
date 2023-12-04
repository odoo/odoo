/** @odoo-module */

export function productEventAvailableSeats(name, quantity){
    return [
        {
            content: `event product has ${quantity} seats available`,
            trigger: `.product-list .badge:contains("${quantity}") ~ .product-content:contains("${name}")` ,
            run: () => {},
        }
    ];
}
export function isShownCustomerNeeded(){
    return [
        {
            content: `show the customer needed pop up`,
            trigger: `.pos .popup-confirm .title:contains('Customer needed')`,
            run: () => {},
        },
        {
            content: `click ok on the customer needed popup`,
            trigger: `.pos .popup-confirm .button:contains('Ok')`,
        },
        {
            content: "partner screen is shown",
            trigger: ".pos-content .partnerlist-screen",
            run: () => {},
        },
    ];
}
