import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

const EXCLUDE_IF_NOT_REGISTERED = ["AE", "SA"];
const GCC_COUNTRIES = ["SA", "AE", "BH", "OM", "QA", "KW"];

patch(PosStore.prototype, {
    getReceiptHeaderData(order) {
        const country = this.company.country_id?.code;
        const useGCCReport =
            GCC_COUNTRIES.includes(country) &&
            (this.company.vat || !EXCLUDE_IF_NOT_REGISTERED.includes(country));
        return {
            ...super.getReceiptHeaderData(...arguments),
            gcc_cashier: order?.getCashierName() || this.get_cashier()?.name,
            show_title: Boolean(order),
            useGCCReport,
        };
    },
});
