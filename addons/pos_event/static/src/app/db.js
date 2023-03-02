/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosDB}  from "@point_of_sale/js/db";

patch(PosDB.prototype, "pos_event.PosDB", {
    //@override
    _isProductDisplayable(product) {
        return this._super(...arguments) && product.detailed_type !== "event";
    },
});
