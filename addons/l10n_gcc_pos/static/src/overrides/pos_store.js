import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    getReceiptHeaderData(order) {
        return {
            ...super.getReceiptHeaderData(...arguments),
            is_gcc_country: ["SA", "AE", "BH", "OM", "QA", "KW"].includes(
                this.company.country_id?.code
            ),
            gcc_cashier: order?.getCashierName() || this.get_cashier()?.name,
            show_title: Boolean(order),
        };
    },
});
