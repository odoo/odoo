/** @odoo-module */

import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { BalanceButton } from "@pos_six/js/BalanceButton";
import { patch } from "@web/core/utils/patch";

patch(Navbar, "pos_six.Navbar", {
    components: { ...Navbar.components, BalanceButton },
});
