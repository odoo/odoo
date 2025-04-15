/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    getReceiptHeaderData(order) {
        const result = super.getReceiptHeaderData(...arguments);
        if (order && this.company?.country?.code === "SA") {
            result.is_settlement = order.is_settlement();
            if (!result.is_settlement) {
                const codeWriter = new window.ZXing.BrowserQRCodeSvgWriter();
                const qr_values = order.compute_sa_qr_code(
                    result.company.name,
                    result.company.vat,
                    order.date_order.toISO(),
                    order.get_total_with_tax(),
                    order.get_total_tax()
                );
                const qr_code_svg = new XMLSerializer().serializeToString(
                    codeWriter.write(qr_values, 150, 150)
                );
                result.qr_code = "data:image/svg+xml;base64," + window.btoa(qr_code_svg);
            }
        }
        return result;
    },
});
