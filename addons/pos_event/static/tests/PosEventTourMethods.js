/** @odoo-module */

import { createTourMethods } from "@point_of_sale/../tests/tours/helpers/utils";
class Do {
}

class Check {

    productEventAvailableSeats(name, quantity){
        return [
            {
                content: `event product has ${quantity} seats available`,
                trigger: `.product-list .badge:contains("${quantity}") ~ .product-content:contains("${name}")` ,
                run: () => {},
            }
        ];
    }
    isShownCustomerNeeded(){
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

}
class Execute {
}

// FIXME: this is a horrible hack to export an object as named exports.
// eslint-disable-next-line no-undef
Object.assign(__exports, createTourMethods("PosEvent", Do, Check, Execute));
