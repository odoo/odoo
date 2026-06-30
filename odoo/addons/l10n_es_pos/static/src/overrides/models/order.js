/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { Order } from "@point_of_sale/app/store/models";

patch(Order.prototype, {
    canBeSimplifiedInvoiced() {
        return (
            this.pos.config.is_spanish &&
            this.env.utils.roundCurrency(this.get_total_with_tax()) <
                this.pos.config.l10n_es_simplified_invoice_limit
        );
    },
    wait_for_push_order() {
        return this.pos.config.is_spanish ? true : super.wait_for_push_order(...arguments);
    },
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        if (this.pos.config.is_spanish) {
            json.is_l10n_es_simplified_invoice = this.is_l10n_es_simplified_invoice;
        }
        return json;
    },
});
