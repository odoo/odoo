/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

const { DateTime } = luxon;

patch(PosStore.prototype, {
     getPrintingChanges(order, diningModeUpdate) {
        const time = DateTime.now().toFormat("dd/MM/yyyy HH:mm");
        return {
            table_name: order.table_id ? order.table_id.table_number : "",
            floor_name: order.table_id?.floor_id.name || "",
            config_name: order.config.name,
            time: time,
            tracking_number: order.tracking_number,
            takeaway: order.config.takeaway && order.takeaway,
            employee_name: order.employee_id?.name || order.user_id?.name,
            order_note: order.general_note,
            diningModeUpdate: diningModeUpdate,
        };
    },

    async showLoginScreen() {
        this.showScreen("FloorScreen");
        this.reset_cashier();
        this.showScreen("LoginScreen");
        this.dialog.closeAll();
    }


});