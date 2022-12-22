/** @odoo-module */

import PosDB from "@point_of_sale/js/db";

const super_isProductDisplayable = PosDB.prototype._isProductDisplayable;
PosDB.include({
    //@override
    _isProductDisplayable(product) {
        return super_isProductDisplayable.apply(this, arguments) && product.detailed_type !== "event";
    }
});