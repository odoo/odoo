import { PosStore } from "@point_of_sale/app/store/pos_store";
import { qrCodeSrc } from "@point_of_sale/utils";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    getReceiptHeaderData(order) {
        const result = super.getReceiptHeaderData(...arguments);
        if (order && order.isSACompany) {
            result.is_settlement = order.is_settlement();
            if (!result.is_settlement) {
                const not_legal =
                    !order.l10n_sa_invoice_qr_code_str ||
                    order.l10n_sa_invoice_edi_state !== "sent";
                result.not_legal = not_legal;
                result.qr_code = !not_legal ? qrCodeSrc(order.l10n_sa_invoice_qr_code_str) : "";
            }
        }
        return result;
    },
});
