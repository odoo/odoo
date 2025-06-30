import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { computeSAQRCode } from "@l10n_sa_pos/app/utils/qr";

patch(PosStore.prototype, {
    getReceiptHeaderData(order) {
        const result = super.getReceiptHeaderData(...arguments);
        const company = this.company;
        if (order && company?.country_id?.code === "SA") {
            result.is_settlement = order.is_settlement();
            if (!result.is_settlement) {
                const codeWriter = new window.ZXing.BrowserQRCodeSvgWriter();
                const qr_values = computeSAQRCode(
                    company.name,
                    company.vat,
                    order.date_order,
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
