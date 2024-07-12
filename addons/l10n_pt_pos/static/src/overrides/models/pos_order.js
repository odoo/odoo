import { patch } from "@web/core/utils/patch";

import { PosOrder } from "@point_of_sale/app/models/pos_order";

patch(PosOrder.prototype, {
    isPortugueseCompany() {
        return this.company.account_fiscal_country_id?.code === "PT";
    },

    /**
     * Sold to a final consumer: no customer, or one without a NIF or with the generic 999999990,
     * which is kept for the SAF-T only and never printed (Despacho 8632/2014 2.2.5, FAQ 4730).
     */
    l10nPtIsFinalConsumer() {
        return !this.partner_id?.vat || this.l10nPtCustomerNif() === "999999990";
    },

    /** The digits of the customer's NIF, or "": a partner without one has ``vat === false``. */
    l10nPtCustomerNif() {
        return (this.partner_id?.vat || "").replace(/\D/g, "");
    },

    /**
     * The generic final consumer (the till's, or any partner with the generic NIF 999999990): its
     * name and address are no buyer's, so the receipt prints only "Consumidor final".
     */
    l10nPtIsGenericFinalConsumer() {
        return Boolean(
            this.partner_id &&
                (this.partner_id.id === this.config._l10n_pt_final_consumer_id ||
                    this.l10nPtCustomerNif() === "999999990")
        );
    },

    /** The tax exemption mentions printed below the total: each exemption code with its legal mention. */
    l10nPtTaxExemptionMentions() {
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
