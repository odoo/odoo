/** @odoo-module */
import { useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";

const selfOrderService = {
    dependencies: ["rpc"],
    async start(env, { rpc }) {
        const config = session.pos_self_order;
        const object = {
            config,
        };
        return object;
    },
};
registry.category("services").add("self_order", selfOrderService);

export function useSelfOrder() {
    return useState(useService("self_order"));
}
