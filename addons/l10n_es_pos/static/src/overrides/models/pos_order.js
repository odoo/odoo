import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { roundCurrency } from "@point_of_sale/app/models/utils/currency";

patch(PosOrder.prototype, {
    canBeSimplifiedInvoiced() {
        return (
            this.config.is_spanish &&
            roundCurrency(this.get_total_with_tax(), this.currency) <
                this.config.l10n_es_simplified_invoice_limit
        );
    },
    wait_for_push_order() {
        return this.config.is_spanish ? true : super.wait_for_push_order(...arguments);
    },
});
