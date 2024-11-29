import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(PosOrder.prototype, {
    get isGccCountry() {
        return ["SA", "AE", "BH", "OM", "QA", "KW"].includes(this.company.country_id?.code);
    },

    export_for_printing(baseUrl, headerData) {
        const results = super.export_for_printing(...arguments);
        results.is_gcc_country = this.isGccCountry;
        if (results.is_gcc_country) {
            results.label_total = _t("TOTAL / اﻹجمالي");
            results.label_rounding = _t("Rounding / التقريب");
            results.label_change = _t("CHANGE / الباقي");
            results.label_discounts = _t("Discounts / الخصومات");
        }
        return results;
    },
});
