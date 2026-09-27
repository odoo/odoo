/** @odoo-module **/

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
        return unavailableQty + (combination.unavailable_kit_qty || 0);
    },
});
