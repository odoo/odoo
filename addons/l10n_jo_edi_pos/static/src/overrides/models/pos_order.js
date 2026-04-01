import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { qrCodeSrc } from "@point_of_sale/utils";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    l10nJoEdiPosQrSrc() {
        return qrCodeSrc(this.l10n_jo_edi_pos_qr);
    },
});
