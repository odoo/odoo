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

    get taxExemptionReasons() {
        // Select unique tax exemption reason codes in order
        const reasons = new Set(
            this.getOrderlines()
                .map((line) => line.tax_ids)
                .flat()
                .filter((tax) => tax.l10n_pt_tax_exemption_reason)
                .map((tax) => tax.l10n_pt_tax_exemption_reason)
        );
        // Map tax exemption codes to their label, returning a sorted array
        const exemptionReasonMap = this.session._l10n_pt_tax_exemption_reason_selection;
        return Array.from(reasons)
            .map((reason) => exemptionReasonMap[reason])
            .filter((label) => label)
            .sort();
    },
});
