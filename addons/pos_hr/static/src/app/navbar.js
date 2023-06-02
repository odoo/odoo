/** @odoo-module */

import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { HeaderLockButton } from "@pos_hr/js/HeaderLockButton";
import { patch } from "@web/core/utils/patch";

patch(Navbar, "pos_hr.Navbar", {
    components: { ...Navbar.components, HeaderLockButton },
});
