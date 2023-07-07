/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosDB}  from "@point_of_sale/app/store/db";

patch(PosDB.prototype, {
    //@override
    shouldAddProduct(product, list) {
        return super.shouldAddProduct(...arguments) && product.detailed_type !== "event";
    },
});
