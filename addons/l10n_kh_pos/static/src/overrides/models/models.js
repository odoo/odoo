/** @odoo-module */

import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";
import { formatMonetary } from "@web/views/fields/formatters";

patch(Order.prototype, {
    set_invoice_name(invoice_name){
        this.invoice_name = invoice_name;
    },

    get_invoice_name(){
        return this.invoice_name;
    },

    export_for_printing() {
        const data = super.export_for_printing(...arguments)

        if (!this.pos.config.khmer_receipt) return data;

        const options = {
            currencyId: this.pos.currency_khr.id,
            noSymbol: false,
        }
        return {
            ...data,
            date: new luxon.DateTime(data.date).toFormat("dd/MM/yy hh:mm:ss"),
            shippingDate: data.shippingDate && new luxon.DateTime(data.shippingDate).toFormat("dd/MM/yy"),
            invoice_name: this.get_invoice_name(),
            khmer_receipt: this.pos.config.khmer_receipt,
            total_amount_khr: formatMonetary(this.pos.company.rate_to_khr * this.get_total_with_tax(), options),
            rate_to_khr: formatMonetary(this.pos.company.rate_to_khr, options)
        };
    },

    // Override so that _finalizeValidation can trigger postPushOrderResolve
    wait_for_push_order() {
        return this.pos.config.khmer_receipt ? true : super.wait_for_push_order(...arguments)
    }
})
