import { EventBus, Plugin, useListener } from "@odoo/owl";

export class TimeOffPlugin extends Plugin {
    bus = new EventBus();

    /**
     * @param {() => any} handler
     */
    onUpdateDashboard(handler) {
        useListener(this.bus, "update_dashboard", handler);
    }

    updateDashboard() {
        this.bus.trigger("update_dashboard");
    }
}
