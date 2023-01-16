/** @odoo-module */

import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { HeaderLockButton } from "../js/HeaderLockButton";
import { patch } from "@web/core/utils/patch";

patch(Navbar, "pos_hr.Navbar", {
    components: { ...Navbar.components, HeaderLockButton },
});
