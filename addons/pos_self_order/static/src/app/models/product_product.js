/** @odoo-module */

import { ProductProduct } from "@point_of_sale/app/models/product_product";
import { patch } from "@web/core/utils/patch";

patch(ProductProduct.prototype, {
    get_price(pricelist, quantity, ...args) {
        if (this._hasCostBasedPricelistRule(pricelist, quantity)) {
            // lst_price is replaced with the server-computed selling price for the
            // self-order pricelist. Never send standard_price to the public client.
            return this.lst_price;
        }
        return super.get_price(pricelist, quantity, ...args);
    },

    _hasCostBasedPricelistRule(pricelist, quantity, seenPricelists = new Set()) {
        if (!pricelist || seenPricelists.has(pricelist.id)) {
            return false;
        }
        seenPricelists.add(pricelist.id);

        const rule = this.getPricelistRule(pricelist, quantity);
        if (!rule) {
            return false;
        }
        if (rule.base === "standard_price") {
            return true;
        }
        return (
            rule.base === "pricelist" &&
            rule.base_pricelist_id &&
            this._hasCostBasedPricelistRule(rule.base_pricelist_id, quantity, seenPricelists)
        );
    },
});
