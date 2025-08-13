/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import { patch } from '@web/core/utils/patch';
import { ProductPage } from '@website_sale/interactions/product_page';

patch(ProductPage.prototype, {
    /**
     * Override of `website_sale_mrp` to check the product's stock influenced by kits.
     *
     * @param {Object} combination
     */
    async _getUnavailableQty(combination) {
        const unavailableQty = await super._getUnavailableQty(combination);
        const kitUnavailableQty = await rpc(
            "/website_sale_mrp/get_unavailable_qty_from_kits",
            combination
        );
        return unavailableQty + kitUnavailableQty;
    },
});
