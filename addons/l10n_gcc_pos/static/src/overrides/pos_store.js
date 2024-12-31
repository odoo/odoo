import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    getReceiptHeaderData(order) {
        const result = super.getReceiptHeaderData(...arguments);
        const is_gcc_country = ["SA", "AE", "BH", "OM", "QA", "KW"].includes(
            this.company.country_id?.code
        );
        return {
            ...result,
            is_gcc_country: is_gcc_country,
            cashier: is_gcc_country
                ? order?.getCashierName() || this.get_cashier()?.name
                : result.cashier,
        };
    },
});
