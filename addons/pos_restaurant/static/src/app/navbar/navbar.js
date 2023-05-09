/** @odoo-module */

import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { BackToFloorButton } from "./BackToFloorButton";

patch(Navbar.components, "pos_restaurant.Navbar components", { BackToFloorButton });
patch(Navbar.prototype, "pos_restaurant.Navbar", {
    /**
     * If no table is set to pos, which means the current main screen
     * is floor screen, then the order count should be based on all the orders.
     */
    get orderCount() {
        const { globalState } = this.pos;
        if (globalState.config.module_pos_restaurant && globalState.table) {
            return globalState.getTableOrders(globalState.table.id).length;
        }
        return this._super(...arguments);
    },
    _shouldLoadOrders() {
        return (
            this._super() ||
            (this.pos.globalState.config.module_pos_restaurant && !this.pos.globalState.table)
        );
    },
    onSwitchButtonClick() {
        this.pos.globalState.floorPlanStyle =
            this.pos.globalState.floorPlanStyle == "kanban" ? "default" : "kanban";
    },
    toggleEditMode() {
        this.pos.globalState.toggleEditMode();
    },
});
