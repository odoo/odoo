/* @odoo-module */

import { PosModel } from "@point_of_sale/app/base_models/base";
import { roundDecimals } from "@web/core/utils/numbers";

export class BasePayment extends PosModel {
    setup(obj, options) {
        super.setup(obj);
        this.payment_method = options.payment_method;
        this.amount = 0;
        this.ticket = "";
    }

    get name() {
        return this.payment_method.name;
    }

    /**
     * Set additional info to be printed on the receipts. value should
     * be compatible with both the QWeb and ESC/POS receipts.
     *
     * @param {string} value - receipt info
     */
    set_receipt_info(value) {
        this.ticket += value;
    }

    set_amount(value) {
        this.amount = roundDecimals(parseFloat(value) || 0, this.env.cache.currency.decimal_places);
    }

    get_amount() {
        return this.amount;
    }

    //exports as JSON for receipt printing
    export_for_printing() {
        return {
            amount: this.get_amount(),
            name: this.name,
            ticket: this.ticket,
        };
    }
}
