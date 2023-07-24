/** @odoo-module */
import { useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Order } from "@pos_self_order/common/models/order";
import { Combo } from "@pos_self_order/common/models/combo";
import { selfOrderCommon } from "@pos_self_order/common/self_order_service";

export class selfOrder extends selfOrderCommon {
    constructor(...args) {
        super(...args);
        this.ready = this.setup(...args).then(() => this);
    }

    async setup(...args) {
        this.comboByIds = {};

        await super.setup(...args);

        this.bus_service.addChannel(`pos_config-${this.access_token}`);
        this.bus_service.addEventListener("notification", ({ detail }) => {
            for (const message of detail) {
                this.dispatchMessage(message);
            }
        });

        this.currentLanguage = this.kiosk_available_languages.find(
            (l) => l.code === this.cookie.current.frontend_lang
        );

        if (this.kiosk_default_language && !this.currentLanguage) {
            this.currentLanguage = this.kiosk_default_language;
        }

        this.cookie.setCookie("frontend_lang", this.currentLanguage.code);

        this.currentCategory = this.pos_category.length > 0 ? this.pos_category[0].name : null;
        // required information to send an order
        this.paymentError = false;
        this.tablePadNumber = null;
        this.currentOrder = new Order({});
        this.eatingLocation = "in"; // (in, out) in by default because out can be disabled in the config
    }

    dispatchMessage(message) {
        const payload = message.payload;
        const type = message.type;

        if (type === "status") {
            if (payload.status === "closed") {
                this.pos_session = [];
            } else {
                // reload to get potential new settings
                // more easier than RPC for now
                window.location.reload();
            }
            this.isSession();
        } else if (type === "payment_status") {
            if (payload.payment_result === "Success") {
                this.updateOrderFromServer(payload.order);
                this.router.navigate("payment_success");
            } else {
                this.paymentError = true;
            }
        }
    }

    updateOrderFromServer(order) {
        this.currentOrder.updateDataFromServer(order);
    }

    initData() {
        super.initData();

        this.combos = this.combos.map((c) => {
            const combo = new Combo(c);
            this.comboByIds[combo.id] = combo;
            return combo;
        });
    }

    isSession() {
        if (!this.pos_session || !this.pos_session.id) {
            this.router.navigate("closed");
        } else if (this.router.activeSlot === "closed") {
            this.router.navigate("default");
        }
    }

    isOrder() {
        if (!this.currentOrder || !this.currentOrder.lines.length) {
            this.router.navigate("default");
        }
    }
}

export const selfOrderService = {
    dependencies: ["rpc", "notification", "router", "bus_service", "cookie"],
    async start(env, { rpc, notification, router, bus_service, cookie }) {
        return new selfOrder(env, rpc, notification, router, bus_service, cookie).ready;
    },
};

registry.category("services").add("self_order_kiosk", selfOrderService);

export function useselfOrder() {
    return useState(useService("self_order_kiosk"));
}
