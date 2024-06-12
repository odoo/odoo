/** @odoo-module */

import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { patch } from "@web/core/utils/patch";

patch(Navbar.prototype, {
    _shouldLoadOrders() {
        return super._shouldLoadOrders() || this.pos.company_has_self_ordering;
    },
});
