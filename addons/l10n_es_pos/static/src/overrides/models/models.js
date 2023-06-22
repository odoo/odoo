/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { Order } from "@point_of_sale/app/store/models";
import { identifyError } from "@point_of_sale/app/errors/error_handlers";
import { ConnectionLostError } from "@web/core/network/rpc_service";

patch(Order.prototype, {
    /**
     * We'll get the sequence number from DB only when we're online.
     * Otherwise the sequence will run on the client side until the
     * orders are synced.
     */
    async set_simple_inv_number() {
        try {
            const number = await this.pos.get_simple_inv_next_number();
            this.pos._set_simplified_invoice_number(number);
        } catch (error) {
            if (!(identifyError(error) instanceof ConnectionLostError)) {
                throw error;
            }
        } finally {
            this.l10n_es_unique_id = this.pos._get_simplified_invoice_number();
        }
    },

    get_base_by_tax() {
        const base_by_tax = {};
        this.get_orderlines().forEach(function (line) {
            const tax_detail = line.get_tax_details();
            const base_price = line.get_price_without_tax();
            if (tax_detail) {
                Object.keys(tax_detail).forEach(function (tax) {
                    if (Object.keys(base_by_tax).includes(tax)) {
                        base_by_tax[tax] += base_price;
                    } else {
                        base_by_tax[tax] = base_price;
                    }
                });
            }
        });
        return base_by_tax;
    },
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        if (!this.pos.config.is_spanish) {
            return;
        }
        this.l10n_es_unique_id = json.l10n_es_unique_id;
    },
    export_as_JSON() {
        const res = super.export_as_JSON(...arguments);
        if (!this.pos.config.is_spanish) {
            return res;
        }
        if (!this.is_to_invoice()) {
            res.l10n_es_unique_id = this.l10n_es_unique_id;
        }
        return res;
    },
    export_for_printing() {
        const result = super.export_for_printing(...arguments);
        if (!this.pos.config.is_spanish) {
            return result;
        }
        const company = this.pos.company;
        result.l10n_es_unique_id = this.l10n_es_unique_id;
        result.to_invoice = this.to_invoice;
        result.company.street = company.street;
        result.company.zip = company.zip;
        result.company.city = company.city;
        result.company.state_id = company.state_id;
        const base_by_tax = this.get_base_by_tax();
        for (const tax of result.tax_details) {
            tax.base = base_by_tax[tax.tax.id];
        }
        return result;
    },
});
