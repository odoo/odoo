/** @odoo-module **/

import { registry } from "./registry";

export const userService = {
    start() {
        const sessionInfo = odoo.session_info;

        const context = {
            ...sessionInfo.user_context,
            uid: sessionInfo.uid,
        };
        return {
            get context() {
                return Object.assign({}, context);
            },
            removeFromContext(key) {
                delete context[key];
            },
            updateContext(update) {
                Object.assign(context, update);
            },
            name: sessionInfo.name,
            userName: sessionInfo.username,
            isAdmin: sessionInfo.is_admin,
            isSystem: sessionInfo.is_system,
            partnerId: sessionInfo.partner_id,
            home_action_id: sessionInfo.home_action_id,
            showEffect: sessionInfo.show_effect,
            get userId() {
                return context.uid;
            },
            get lang() {
                return context.lang;
            },
            get tz() {
                return context.tz;
            },
            get db() {
                const res = {
                    name: sessionInfo.db,
                };
                if ("dbuuid" in sessionInfo) {
                    res.uuid = sessionInfo.dbuuid;
                }
                return res;
            },
        };
    },
};

registry.category("services").add("user", userService);
