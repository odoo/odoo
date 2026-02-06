/** @odoo-module */

import { Patch } from "@web/core/utils/patch";
import { WelcomeScreen } from "@point_of_sale/app/screens/welcome_screen/welcome_screen";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { EatingLocationPage } from "@pos_self_order/app/pages/eating_location_page/eating_location_page";

// Patch Welcome Screen
Patch(WelcomeScreen.prototype, {
    goBackToWebsite() {
        window.location.href = '/';
    }
});

// Patch Ticket Screen
Patch(TicketScreen.prototype, {
    goBackToWebsite() {
        window.location.href = '/';
    }
});

// Patch EatingLocationPage to check delivery availability
Patch(EatingLocationPage.prototype, {
    get presets() {
        let all = super.presets;
        if (!this.selfOrder.config.accept_remote_orders) {
            all = all.filter((item) => item.service_at !== "delivery");
        }
        return all;
    },
    selectPreset(preset) {
        if (preset.service_at === 'delivery' && !this.selfOrder.config.accept_remote_orders) {
            console.warn("Delivery is currently unavailable.");
            return;
        }
        super.selectPreset(preset);
    }
});
