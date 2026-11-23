import DeviceIdentifierSequence from "@point_of_sale/app/utils/devices_identifier_sequence";
import { patch } from "@web/core/utils/patch";

patch(DeviceIdentifierSequence.prototype, {
    l10nInUseNextB2CInvoiceNumber(isRefund) {
        const key = isRefund ? "l10n_in_next_b2c_refund_number" : "l10n_in_next_b2c_invoice_number";
        const number = this.data[key] || 1;
        this.save({ [key]: number + 1 });
        return number;
    },
});
