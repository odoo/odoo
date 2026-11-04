/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import VariantMixin from "@website_sale_stock/js/variant_mixin";

const oldGetUnavailableQty = VariantMixin._getUnavailableQty;

/**
 * Get unavailable stock related to kit products of the cart.
 * @override
 */
VariantMixin._getUnavailableQty = async function (combination) {
    const unavailableQty = await oldGetUnavailableQty.apply(this, arguments);
    const kitUnavailableQty = await rpc(
        "/website_sale_mrp/get_unavailable_qty_from_kits",
        combination
    );
    return unavailableQty + kitUnavailableQty;
};
