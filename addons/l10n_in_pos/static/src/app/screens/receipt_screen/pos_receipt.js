import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(OrderReceipt.prototype, {
    _getAdditionalLineInfo(line) {
        const info = super._getAdditionalLineInfo(line);
        if (line.l10n_in_hsn_code && this.header.company.country_id?.code === "IN") {
            info.push({
                class: "pos-receipt-hsn-code",
                value: _t("HSN: ") + line.l10n_in_hsn_code,
            });
        }
        return info;
    },
});
