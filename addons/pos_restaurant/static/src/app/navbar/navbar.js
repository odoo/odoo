/** @odoo-module */

import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { BackToFloorButton } from "./BackToFloorButton";

patch(Navbar.components, "pos_restaurant.Navbar components", { BackToFloorButton });
patch(Navbar.prototype, "pos_restaurant.Navbar", {
    async onTicketButtonClick() {
        if (
            this.env.pos.config.iface_floorplan &&
            !this.isTicketScreenShown &&
            !this.env.pos.table
        ) {
            try {
                this.env.pos.setLoadingOrderState(true);
                await this.env.pos._syncAllOrdersFromServer();
            } finally {
                this.env.pos.setLoadingOrderState(false);
                this.pos.showScreen("TicketScreen");
            }
        } else {
            return this._super(...arguments);
        }
    },
    /**
     * If no table is set to pos, which means the current main screen
     * is floor screen, then the order count should be based on all the orders.
     */
    get orderCount() {
        if (!this.env.pos || !this.env.pos.config) {
            return 0;
        }
        if (this.env.pos.config.iface_floorplan && this.env.pos.table) {
            return this.env.pos.getTableOrders(this.env.pos.table.id).length;
        }
        return this._super(...arguments);
    },
});
