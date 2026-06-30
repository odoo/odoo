import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { roundCurrency } from "@point_of_sale/app/models/utils/currency";

patch(PosOrder.prototype, {
    canBeSimplifiedInvoiced() {
        return (
            this.config.is_spanish &&
            roundCurrency(this.priceIncl, this.currency) <
                this.company.l10n_es_simplified_invoice_limit
        );
    },
    waitForPushOrder() {
        return this.config.is_spanish ? true : super.waitForPushOrder(...arguments);
    },
});
