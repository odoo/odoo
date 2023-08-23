/** @odoo-module */

import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/receipt";
import { patch } from "@web/core/utils/patch";

patch(OrderReceipt.prototype, "l10n_pt_pos.OrderReceipt", {
    get receiptEnv() {
        const receiptRenderEnv = this._super(...arguments);
        const receipt = receiptRenderEnv.receipt;
        const country = receiptRenderEnv.order.pos.company.country;
        receipt.isCountryPortugal = country && country.code === 'PT';
        if (receipt.isCountryPortugal && receipt.l10nPtPosInalterableHash) {
            const codeWriter = new window.ZXing.BrowserQRCodeSvgWriter();
            const qrCodeSvg = new XMLSerializer().serializeToString(
                codeWriter.write(receipt.l10nPtPosQrCodeStr, 200, 200)
            );
            receipt.l10nPtPosQrCode = "data:image/svg+xml;base64," + window.btoa(qrCodeSvg);
        }
        return receiptRenderEnv;
    },
});
