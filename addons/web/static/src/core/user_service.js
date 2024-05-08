/** @odoo-module **/

import { registry } from "./registry";
import { session } from "@web/session";

export const userService = {
    dependencies: ["rpc"],
    async: ["hasGroup"],
    start(env, { rpc }) {
        const groupProms = {};

        const context = {
            ...session.user_context,
            // the user id is in uid in backend session_info and in user_id in frontend session_info
            uid: session.uid || session.user_id,
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
            hasGroup(group) {
                if (!context.uid) {
                    return Promise.resolve(false);
                }
                if (!groupProms[group]) {
                    groupProms[group] = rpc("/web/dataset/call_kw/res.users/has_group", {
                        model: "res.users",
                        method: "has_group",
                        args: [group],
                        kwargs: { context },
                    });
                }
                return groupProms[group];
            },
            name: session.name,
            userName: session.username,
            isAdmin: session.is_admin,
            isSystem: session.is_system,
            partnerId: session.partner_id,
            home_action_id: session.home_action_id,
            showEffect: session.show_effect,
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
                    name: session.db,
                };
                if ("dbuuid" in session) {
                    res.uuid = session.dbuuid;
                }
                return res;
            },
        };
    },
};

registry.category("services").add("user", userService);
