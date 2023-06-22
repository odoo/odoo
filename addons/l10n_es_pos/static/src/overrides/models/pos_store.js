/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { ConnectionLostError } from "@web/core/network/rpc_service";

patch(PosStore.prototype, {
    /**
     * @override
     */
    async setup() {
        await super.setup(...arguments);
        if (!this.config.is_spanish) {
            return;
        }
        this.pushed_simple_invoices = [];
    },

    /**
     * @override
     */
    async _processData(loadedData) {
        await super._processData(...arguments);
        if (!this.config.is_spanish) {
            return;
        }
        this.l10n_es_simplified_invoice = loadedData["l10n_es_simplified_invoice"];
    },

    get_simple_inv_next_number() {
        // If we had pending orders to sync we want to avoid getting the next number
        // from the DB as we'd be overlapping the sequence.
        if (this.db.get_orders().length) {
            return Promise.reject(new ConnectionLostError());
        }
        return this.orm.silent.call("pos.config", "get_l10n_es_simplified_invoice_number", [
            [this.config.id],
        ]);
    },
    _update_sequence_number() {
        ++this.l10n_es_simplified_invoice.number;
    },
    push_simple_invoice(order) {
        if (this.pushed_simple_invoices.indexOf(order.data.l10n_es_unique_id) === -1) {
            this.pushed_simple_invoices.push(order.data.l10n_es_unique_id);
            this._update_sequence_number();
        }
    },
    _flush_orders(orders) {
        // Save pushed orders numbers
        if (!this.config.is_spanish) {
            return super._flush_orders(...arguments);
        }
        orders.forEach((order) => {
            if (!order.data.to_invoice) {
                this.push_simple_invoice(order);
            }
        });
        return super._flush_orders(...arguments);
    },
    _set_simplified_invoice_number(number) {
        this.l10n_es_simplified_invoice.number = number;
    },
    _get_simplified_invoice_number() {
        return (
            this.l10n_es_simplified_invoice.prefix +
            this.l10n_es_simplified_invoice.number
                .toString()
                .padStart(this.l10n_es_simplified_invoice.padding, "0")
        );
    },
});
