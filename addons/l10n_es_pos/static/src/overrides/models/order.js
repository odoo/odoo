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
    async updateWithServerData(data) {
        await super.updateWithServerData(data);
        if (data.l10n_es_simplified_invoice_number) {
            this.invoice_name = data.l10n_es_simplified_invoice_number;
        }
    },
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        if (json.l10n_es_simplified_invoice_number) {
            this.invoice_name = json.l10n_es_simplified_invoice_number;
        }
    },
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        if (this.pos.config.is_spanish) {
            json.is_l10n_es_simplified_invoice = this.is_l10n_es_simplified_invoice;
        }
        return json;
    },
});
