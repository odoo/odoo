/** @odoo-module */

import { RemoteDisplay } from "@point_of_sale/app/customer_display/customer_display_service";
import { patch } from "@web/core/utils/patch";

patch(RemoteDisplay, {
    serviceDependencies: [...RemoteDisplay.serviceDependencies, "iot_longpolling"],
});
patch(RemoteDisplay.prototype, {
    setup(pos, { iot_longpolling }) {
        super.setup(...arguments);
        this.iotLongpolling = iot_longpolling;
    },
    /**
     * @override replaces the original behaviour completely
     */
    async connect() {
        this.hardwareProxy.deviceControllers.display.action({
            action: "take_control",
            html: await this.pos.customerDisplayHTML(),
        });
    },
    /**
     * @override replaces the original behaviour completely
     */
    async update() {
        return this.hardwareProxy.deviceControllers?.display?.action({
            action: "customer_facing_display",
            html: await this.pos.customerDisplayHTML(),
        });
    },
    /**
     * @override replaces the original behaviour completely
     */
    updateStatus() {
        if (!this.hardwareProxy.deviceControllers.display) {
            return;
        }
        this.hardwareProxy.deviceControllers.display.addListener(({ error, owner }) => {
            if (error) {
                this.status = "not_found";
            } else if (owner === this.iotLongpolling._session_id) {
                this.status = "success";
            } else {
                this.status = "warning";
            }
        });
        setTimeout(() => {
            this.hardwareProxy.deviceControllers.display.action({ action: "get_owner" });
        }, 1500);
    },
});
