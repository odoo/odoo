/** @odoo-module */

import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { BackToFloorButton } from "./BackToFloorButton";

patch(Navbar, "pos_restaurant.Navbar", {
    components: { ...Navbar.components, BackToFloorButton },
});
