import { _t } from "@web/core/l10n/translation";
import { ProductInfoPopup } from "@point_of_sale/app/components/popups/product_info_popup/product_info_popup";

import { patch } from "@web/core/utils/patch";

patch(ProductInfoPopup.prototype, {
    get vatLabel() {
        return this.pos.company.country_id.code === "IN" ? _t("GST:") : super.vatLabel;
    },
    get totalVatLabel() {
        return this.pos.company.country_id.code === "IN" ? _t("Total GST:") : super.totalVatLabel;
    },
});
