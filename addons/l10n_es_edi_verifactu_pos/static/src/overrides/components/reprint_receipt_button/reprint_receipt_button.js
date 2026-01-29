/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ReprintReceiptButton } from "@point_of_sale/app/screens/ticket_screen/reprint_receipt_button/reprint_receipt_button";

patch(ReprintReceiptButton.prototype, {
    //@override
    async click() {
        if (!this.props.order) {
            return;
        }
        const order = this.props.order;
        const [res] = await order.fetch_l10n_es_edi_verifactu_qr_code([order.server_id]);
        order.l10n_es_edi_verifactu_qr_code = res.l10n_es_edi_verifactu_qr_code;
        return super.click();
    },
});
