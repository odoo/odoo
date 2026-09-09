import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

const EXCLUDE_IF_NOT_REGISTERED = ["AE", "SA"];
const GCC_COUNTRIES = ["SA", "AE", "BH", "OM", "QA", "KW"];

patch(PosOrder.prototype, {
    get useGCCReport() {
        const country = this.company.country_id?.code;
        return (
            GCC_COUNTRIES.includes(country) &&
            (this.company.vat || !EXCLUDE_IF_NOT_REGISTERED.includes(country))
        );
    },
    get showTitle() {
        return this.state !== "draft";
    },
});
