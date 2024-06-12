/** @odoo-module **/

import { registry } from "./registry";
import { session } from "@web/session";
import { Cache } from "./utils/cache";

export const userService = {
    dependencies: ["rpc"],
    async: ["hasGroup"],
    start(env, { rpc }) {
        const groupCache = new Cache((group) => {
            if (!context.uid) {
                return Promise.resolve(false);
            }
            return rpc("/web/dataset/call_kw/res.users/has_group", {
                model: "res.users",
                method: "has_group",
                args: [group],
                kwargs: { context },
            });
        });
        groupCache.cache["base.group_user"] = session.is_internal_user;
        groupCache.cache["base.group_system"] = session.is_system;
        const accessRightCache = new Cache((model, operation) => {
            const url = `/web/dataset/call_kw/${model}/check_access_rights`;
            return rpc(url, {
                model,
                method: "check_access_rights",
                args: [operation, false],
                kwargs: { context },
            });
        });

        const context = {
            ...session.user_context,
            // the user id is in uid in backend session_info and in user_id in frontend session_info
            uid: session.uid || session.user_id,
        };
        let settings = session.user_settings;
        delete session.user_settings;
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
                return groupCache.read(group);
            },
            async checkAccessRight(model, operation) {
                return accessRightCache.read(model, operation);
            },
            get settings() {
                return settings;
            },
            async setUserSettings(key, value) {
                const changedSettings = await env.services.orm.call(
                    "res.users.settings",
                    "set_res_users_settings",
                    [[this.settings.id]],
                    {
                        new_settings: {
                            [key]: value,
                        },
                    }
                );
                Object.assign(settings, changedSettings);
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
