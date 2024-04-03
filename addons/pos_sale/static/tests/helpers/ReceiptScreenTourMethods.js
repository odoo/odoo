odoo.define('pos_sale.tour.ReceiptScreenTourMethods', function (require) {
    'use strict';

    const { createTourMethods } = require('point_of_sale.tour.utils');
    const { Do, Check, Execute } = require('point_of_sale.tour.ReceiptScreenTourMethods');

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

    return createTourMethods('ReceiptScreen', Do, CheckExt, Execute);
});
