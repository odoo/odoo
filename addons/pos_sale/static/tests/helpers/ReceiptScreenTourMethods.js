//** @odoo-module */

import { createTourMethods } from '@point_of_sale/../tests/tours/helpers/utils';
import { Do, Check, Execute } from '@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods';

class DoExt extends Do {}

class CheckExt extends Check{
    checkCustomerNotes(note) {
        return [
            {
                content: `check customer notes`,
                trigger: `.pos-receipt-customer-note:contains(${note})`,
            }
        ];
    }
}
class ExecuteExt extends Execute {}

// FIXME: this is a horrible hack to export an object as named exports.
// eslint-disable-next-line no-undef
Object.assign(__exports, createTourMethods("ReceiptScreen", DoExt, CheckExt, ExecuteExt));
