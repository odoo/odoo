/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    async processServerData() {
        await super.processServerData(...arguments);
        this.account_tag_by_xml_ref_id = this.data.custom.account_tag_by_xml_ref_id
    },

    /**
     * @override
     * @param {Object} tax
     * @param {integer} sign
     * @param {float} factorized_tax_amount
     * @param {float} tax_base_amount
     * @param {float} currency_round
     * @returns {Object}
    */
    _prepare_tax_vals_data(tax, sign, factorized_tax_amount, tax_base_amount, currency_rounding) {
        const tax_vals = super._prepare_tax_vals_data(...arguments);
        tax_vals['repartition_line_ids'] = tax.repartition_line_ids
        tax_vals['tax_rate'] = tax.amount
        return tax_vals
    },
});
