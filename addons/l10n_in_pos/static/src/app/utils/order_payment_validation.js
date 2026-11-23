import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { patch } from "@web/core/utils/patch";

const { DateTime } = luxon;

patch(OrderPaymentValidation.prototype, {
    async finalizeValidation() {
        if (this.order.isL10nInB2COrder && !this.order.l10n_in_b2c_invoice_number) {
            this.assignL10nInB2CInvoiceNumber();
        }
        return super.finalizeValidation(...arguments);
    },

    /**
     * The 4 digits identifying the PoS and the device in a B2C invoice number, so that
     * the number stays within the 16 characters allowed by the GST portal.
     */
    get l10nInConfigIdentifier() {
        const configDigits = `${this.pos.config.id}`.padStart(2, "0");
        if (configDigits.length >= 4) {
            return configDigits.slice(-4);
        }
        const width = 4 - configDigits.length;
        return configDigits + `${this.pos.device.identifier}`.padStart(width, "0").slice(-width);
    },

    /**
     * Keep in sync with _l10n_in_format_b2c_invoice_number.
     */
    assignL10nInB2CInvoiceNumber() {
        const number = this.pos.device.l10nInUseNextB2CInvoiceNumber(this.order.isRefund);

        const prefix = this.order.isRefund ? "R" : this.pos.config.l10n_in_b2c_invoice_prefix;
        const year2Digits = DateTime.now().year.toString().slice(-2);
        const sequence = `${number}`.padStart(7, "0");

        this.order.l10n_in_b2c_invoice_number = `${prefix}${year2Digits}/${this.l10nInConfigIdentifier}/${sequence}`; // e.g. P26/0702/0000001
    },
});
