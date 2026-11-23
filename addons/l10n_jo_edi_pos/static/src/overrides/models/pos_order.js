import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { qrCodeSrc } from "@point_of_sale/utils";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    get canEditPayment() {
        // The refund would reach JoFotara without the mandatory return reason
        return this.company.l10n_jo_edi_pos_enabled ? false : super.canEditPayment;
    },
    l10nJoEdiPosQrSrc() {
        return qrCodeSrc(this.l10n_jo_edi_pos_qr);
    },
});
