import { PrintPopup } from "@point_of_sale/app/components/popups/print_popup/print_popup";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(PrintPopup.prototype, {
    get printList() {
        const list = super.printList;
        if (!this.order.l10nEsPosIsSimplifiedInvoice) {
            return list;
        }
        const spanishLabels = {
            [_t("Full Receipt")]: _t("Simplified Invoice"),
            [_t("Simplified Receipt")]: _t("Receipt"),
        };
        return list.map((item) =>
            spanishLabels[item.label] ? { ...item, label: spanishLabels[item.label] } : item
        );
    },
});
