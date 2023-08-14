/** @odoo-module */

import { createTourMethods } from "@point_of_sale/../tests/tours/helpers/utils";
import * as Order from "@point_of_sale/../tests/tours/helpers/generic_components/OrderWidgetMethods";

class Do {
    clickOrderline(productName) {
        return Order.hasLine({ productName, run: "click" });
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
        return Order.hasLine({
            productName: name,
            quantity: splitQuantity != 0 ? `${splitQuantity} / ${totalQuantity}` : totalQuantity,
        });
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
