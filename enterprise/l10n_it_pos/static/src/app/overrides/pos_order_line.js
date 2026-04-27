import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";
import { isFiscalPrinterConfigured } from "./helpers/utils";

patch(PosOrderline.prototype, {
    // EXTENDS 'point_of_sale'
    prepareBaseLineForTaxesComputationExtraValues(customValues = {}) {
        const extraValues = super.prepareBaseLineForTaxesComputationExtraValues(customValues);
        extraValues.l10n_it_epson_printer = isFiscalPrinterConfigured(this.order_id.config);
        return extraValues;
    },
});
