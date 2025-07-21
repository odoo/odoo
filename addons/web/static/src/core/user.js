import { browser } from "@web/core/browser/browser";
import { pyToJsLocale } from "@web/core/l10n/utils/locales";
import { rpc } from "@web/core/network/rpc";
import { Cache } from "@web/core/utils/cache";
import { session } from "@web/session";
import { ensureArray } from "./utils/arrays";

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
    const settings = user_settings || {};

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

    // Generate caches for has_group and has_access calls
    const getGroupCacheValue = (group, context) => {
        if (!userId) {
            return Promise.resolve(false);
        }
        return rpc("/web/dataset/call_kw/res.users/has_group", {
            model: "res.users",
            method: "has_group",
            args: [userId, group],
            kwargs: { context },
        });
    };
    const getGroupCacheKey = (group) => group;
    const groupCache = new Cache(getGroupCacheValue, getGroupCacheKey);
    if (isInternalUser !== undefined) {
        groupCache.cache["base.group_user"] = Promise.resolve(isInternalUser);
    }
    if (isSystem !== undefined) {
        groupCache.cache["base.group_system"] = Promise.resolve(isSystem);
    }
    const getAccessRightCacheValue = (model, operation, ids, context) => {
        const url = `/web/dataset/call_kw/${model}/has_access`;
        return rpc(url, {
            model,
            method: "has_access",
            args: [ids, operation],
            kwargs: { context },
        });
    };
    const getAccessRightCacheKey = (model, operation, ids) =>
        JSON.stringify([model, operation, ids]);
    const accessRightCache = new Cache(getAccessRightCacheValue, getAccessRightCacheKey);
    const lang = pyToJsLocale(context?.lang);

    const user = {
        name,
        login,
        isAdmin,
        isSystem,
        isInternalUser,
        partnerId,
        homeActionId,
        showEffect,
        userId, // TODO: rename into id?
        writeDate,
        get context() {
            return Object.assign({}, context, { uid: this.userId });
        },
        get lang() {
            return lang;
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
        checkAccessRight(model, operation, ids = []) {
            return accessRightCache.read(model, operation, ensureArray(ids), this.context);
        },
        async setUserSettings(key, value) {
            const model = "res.users.settings";
            const method = "set_res_users_settings";
            const changedSettings = await rpc(`/web/dataset/call_kw/${model}/${method}`, {
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
            Object.assign(settings, changedSettings);
        },
    };

    return user;
}

export const user = _makeUser(session);

const LAST_CONNECTED_USER_KEY = "web.lastConnectedUser";

export const getLastConnectedUsers = () => {
    const lastConnectedUsers = browser.localStorage.getItem(LAST_CONNECTED_USER_KEY);
    return lastConnectedUsers ? JSON.parse(lastConnectedUsers) : [];
};

export const setLastConnectedUsers = (users) => {
    browser.localStorage.setItem(LAST_CONNECTED_USER_KEY, JSON.stringify(users.slice(0, 5)));
};

if (!session.quick_login) {
    browser.localStorage.removeItem(LAST_CONNECTED_USER_KEY);
} else if (user.login && user.login !== "__system__") {
    const users = getLastConnectedUsers();
    const lastConnectedUsers = [
        {
            login: user.login,
            name: user.name,
            partnerId: user.partnerId,
            partnerWriteDate: user.writeDate,
            userId: user.userId,
        },
        ...users.filter((u) => u.userId !== user.userId),
    ];
    setLastConnectedUsers(lastConnectedUsers);
}
delete session.quick_login;
