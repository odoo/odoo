/** @odoo-module */

import { createTourMethods } from "@point_of_sale/../tests/tours/helpers/utils";
import { Do, Check, Execute } from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";

class DoExt extends Do {
    clickQuotationButton() {
        return [
            {
                content: 'click quotation button',
                trigger: '.o_sale_order_button',
            }
        ];
    }

    selectFirstOrder() {
        return [
            {
                content: `select order`,
                trigger: `.order-row .col.name:first`,
            },
            {
                content: `click on select the order`,
                trigger: `.selection-item:contains('Settle the order')`,
            }
        ];
    }
}
class CheckExt extends Check {}

class ExecuteExt extends Execute {}

// FIXME: this is a horrible hack to export an object as named exports.
// eslint-disable-next-line no-undef
Object.assign(__exports, createTourMethods("ProductScreen", DoExt, CheckExt, ExecuteExt));
