/** @odoo-module */

import { createTourMethods } from "@point_of_sale/../tests/tours/helpers/utils";

class Do {
    clickOrderline(name, totalQuantity) {
        let trigger = `li.orderline .product-name:contains("${name}")`;
        if (totalQuantity) {
            trigger += ` ~ .info-list .info:contains("${totalQuantity}")`;
        }
        return [
            {
                content: `click '${name}' orderline with total quantity of '${totalQuantity}'`,
                trigger,
            },
        ];
    }
    clickBack() {
        return [
            {
                content: "click back button",
                trigger: `.splitbill-screen .button.back`,
            },
        ];
    }
    clickPay() {
        return [
            {
                content: "click pay button",
                trigger: `.splitbill-screen .pay-button .button`,
            },
        ];
    }
}

class Check {
    orderlineHas(name, totalQuantity, splitQuantity) {
        return [
            {
                content: `'${name}' orderline has total quantity of '${totalQuantity}'`,
                trigger: `li.orderline .product-name:contains("${name}") ~ .info-list .info:contains("${totalQuantity}")`,
                run: () => {},
            },
            {
                content: `'${name}' orderline has '${splitQuantity}' quantity to split`,
                trigger: `li.orderline .product-name:contains("${name}") ~ .info-list .info em:contains("${splitQuantity}")`,
                run: () => {},
            },
        ];
    }
    subtotalIs(amount) {
        return [
            {
                content: `total amount of split is '${amount}'`,
                trigger: `.splitbill-screen .order-info .subtotal:contains("${amount}")`,
            },
        ];
    }
}

class Execute {}

// FIXME: this is a horrible hack to export an object as named exports.
// eslint-disable-next-line no-undef
Object.assign(__exports, createTourMethods("SplitBillScreen", Do, Check, Execute));
