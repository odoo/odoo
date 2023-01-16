/** @odoo-module */

import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { BackToFloorButton } from "../js/ChromeWidgets/BackToFloorButton";
import { patch } from "@web/core/utils/patch";

patch(Navbar, "pos_restaurant.Navbar", {
    components: { ...Navbar.components, BackToFloorButton },
});
