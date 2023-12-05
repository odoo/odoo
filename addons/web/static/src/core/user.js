/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import { Cache } from "@web/core/utils/cache";
import { session } from "@web/session";

// This file exports an object containing user-related information and functions
// allowing to obtain/alter user-related information from the server.

/**
 * This function exists for testing purposes. We don't want tests to share the
 * same cache. It allows to generate new caches at the beginning of tests.
 *
 * Note: with hoot, this will no longer be necessary.
 *
 * @returns Object
 */
export function _makeUser(session) {
    // Retrieve user-related information from the session
    const {
        home_action_id: homeActionId,
        is_admin: isAdmin,
        is_internal_user: isInternalUser,
        is_system: isSystem,
        name,
        partner_id: partnerId,
        show_effect: showEffect,
        uid: userId,
        username: login,
        user_context: context,
        user_settings,
        partner_write_date: writeDate,
    } = session;
    let settings = user_settings;

    // Delete user-related information from the session, s.t. there's a single source of truth
    delete session.home_action_id;
    delete session.is_admin;
    delete session.is_internal_user;
    delete session.is_system;
    delete session.name;
    delete session.partner_id;
    delete session.show_effect;
    delete session.uid;
    delete session.username;
    delete session.user_context;
    delete session.user_settings;
    delete session.partner_write_date;

    // Generate caches for has_group and check_access_rights calls
    const getGroupCacheValue = (group, context) => {
        if (!userId) {
            return Promise.resolve(false);
        }
        return rpc("/web/dataset/call_kw/res.users/has_group", {
            model: "res.users",
            method: "has_group",
            args: [group],
            kwargs: { context },
        });
    };
    const getGroupCacheKey = (group) => group;
    const groupCache = new Cache(getGroupCacheValue, getGroupCacheKey);
    groupCache.cache["base.group_user"] = Promise.resolve(isInternalUser);
    groupCache.cache["base.group_system"] = Promise.resolve(isSystem);
    const getAccessRightCacheValue = (model, operation, context) => {
        const url = `/web/dataset/call_kw/${model}/check_access_rights`;
        return rpc(url, {
            model,
            method: "check_access_rights",
            args: [operation, false],
            kwargs: { context },
        });
    };
    const getAccessRightCacheKey = (model, operation) => `${model}/${operation}`;
    const accessRightCache = new Cache(getAccessRightCacheValue, getAccessRightCacheKey);

    const user = {
        name,
        login,
        isAdmin,
        isSystem,
        partnerId,
        homeActionId,
        showEffect,
        userId, // TODO: rename into id?
        writeDate,
        get context() {
            return Object.assign({}, context, { uid: this.userId });
        },
        get lang() {
            return this.context.lang;
        },
        get tz() {
            return this.context.tz;
        },
        get settings() {
            return Object.assign({}, settings);
        },
        updateContext(update) {
            Object.assign(context, update);
        },
        hasGroup(group) {
            return groupCache.read(group, this.context);
        },
        checkAccessRight(model, operation) {
            return accessRightCache.read(model, operation, this.context);
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
                    context: this.context,
                },
            });
        },
    };

    return user;
}

export const user = _makeUser(session);
