import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    /** The tax exemption codes of the line's exempt taxes, as printed next to it: "[M07], [M16]". */
    l10nPtTaxExemptionCodes() {
        return this.tax_ids
            .map((tax) =>
                tax.l10n_pt_tax_exemption_reason
                    ? `[${tax.l10n_pt_tax_exemption_reason}]`
                    : undefined
            )
            .filter(Boolean)
            .join(", ");
    },
});
