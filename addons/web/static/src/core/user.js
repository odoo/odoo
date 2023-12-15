/** @odoo-module **/

import { rpc } from "./network/rpc";
import { session } from "@web/session";
import { Cache } from "./utils/cache";

/**
 * This function is meant to be used only in test, to re-generate a fresh user
 * object before each test, based on a patched session.
 *
 * @returns Object
 */
export function _makeUser() {
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
    groupCache.cache["base.group_user"] = Promise.resolve(session.is_internal_user);
    groupCache.cache["base.group_system"] = Promise.resolve(session.is_system);
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
        uid: session.uid,
    };
    let settings = session.user_settings;
    delete session.user_settings;

    return {
        name: session.name,
        userName: session.username,
        isAdmin: session.is_admin,
        isSystem: session.is_system,
        partnerId: session.partner_id,
        home_action_id: session.home_action_id,
        showEffect: session.show_effect,
        get context() {
            return Object.assign({}, context);
        },
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
        get settings() {
            return settings;
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
        checkAccessRight(model, operation) {
            return accessRightCache.read(model, operation);
        },
        async setUserSettings(key, value) {
            const model = "res.users.settings";
            const method = "set_res_users_settings";
            settings = await rpc(`/web/dataset/call_kw/${model}/${method}`, {
                model,
                method,
                args: [[this.settings.id]],
                kwargs: {
                    new_settings: {
                        [key]: value,
                    },
                    context: user.context,
                },
            });
        },
    };
}

export const user = _makeUser();
