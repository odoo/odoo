/** @odoo-module */

import { patch } from "@web/core/utils/patch";

import { PosOrder } from "@point_of_sale/app/models/pos_order";

patch(PosOrder.prototype, {
    isPortugueseCompany() {
        return this.company.country_id?.code === "PT";
    },

    /**
     * Sold to a final consumer: no customer, or one without a NIF or with the generic 999999990,
     * which is kept for the SAF-T only and never printed (Despacho 8632/2014 2.2.5, FAQ 4730).
     */
    l10nPtIsFinalConsumer() {
        const nif = this.partner_id?.vat?.replace(/\D/g, "");
        return !this.partner_id?.vat || nif === "999999990";
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
        // Map tax exemption codes to the reason printed: code and mention
        const exemptionReasonMap = this.session._l10n_pt_tax_exemption_reasons;
        return Array.from(reasons)
            .map((reason) => exemptionReasonMap[reason])
            .filter((label) => label)
            .sort();
    },
});
