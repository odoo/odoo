/** @odoo-module */

import { patch } from "@web/core/utils/patch";

import { PosOrder } from "@point_of_sale/app/models/pos_order";

patch(PosOrder.prototype, {
    isPortugueseCompany() {
        return this.company.country_id?.code === "PT";
    },

    l10nPtPosGetQrCodeData(qrCodeStr) {
        const codeWriter = new window.ZXing.BrowserQRCodeSvgWriter();
        const qdCodeSvg = new XMLSerializer().serializeToString(
            codeWriter.write(qrCodeStr, 200, 200)
        );
        return "data:image/svg+xml;base64," + window.btoa(qdCodeSvg);
    },

    export_for_printing(baseUrl, headerData) {
        const receipt = super.export_for_printing(...arguments);
        if (this.isPortugueseCompany()) {
            receipt["isCountryPortugal"] = true;
            receipt["l10nPtCertificationNumber"] = this.session_id.l10nPtCertificationNumber;
            receipt["l10nPtTrainingMode"] = this.session_id.l10nPtTrainingMode;
            if (this.l10nPtPosInalterableHashShort) {
                receipt["l10nPtPosInalterableHashShort"] = this.l10nPtPosInalterableHashShort;
                receipt["l10nPtPosAtcud"] = this.l10nPtPosAtcud;
                receipt["l10nPtPosQrCodeStr"] = this.l10nPtPosGetQrCodeData(
                    this.l10nPtPosQrCodeStr
                );
            }
        }
        return receipt;
    },
});
