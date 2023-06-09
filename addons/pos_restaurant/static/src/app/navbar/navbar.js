/** @odoo-module */

import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { patch } from "@web/core/utils/patch";

patch(Navbar.prototype, "pos_restaurant.Navbar", {
    /**
     * If no table is set to pos, which means the current main screen
     * is floor screen, then the order count should be based on all the orders.
     */
    get orderCount() {
        if (this.pos.config.module_pos_restaurant && this.pos.table) {
            return this.pos.getTableOrders(this.pos.table.id).length;
        }
        return this._super(...arguments);
    },
    _shouldLoadOrders() {
        return this._super() || (this.pos.config.module_pos_restaurant && !this.pos.table);
    },
    onSwitchButtonClick() {
        this.pos.floorPlanStyle = this.pos.floorPlanStyle == "kanban" ? "default" : "kanban";
    },
    toggleEditMode() {
        this.pos.toggleEditMode();
    },
    showBackButton() {
        return (
            this._super(...arguments) ||
            (this.pos.showBackButton() && this.pos.config.module_pos_restaurant)
        );
    },
});
