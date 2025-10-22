import { browser } from "@web/core/browser/browser";
import { pyToJsLocale } from "@web/core/l10n/utils/locales";
import { rpc } from "@web/core/network/rpc";
import { Cache } from "@web/core/utils/cache";
import { session } from "@web/session";
import { ensureArray, sortBy } from "./utils/arrays";
import { cookie } from "@web/core/browser/cookie";
import { EventBus } from "@odoo/owl";

// This file exports an object containing user-related information and functions
// allowing to obtain/alter user-related information from the server.

export const userBus = new EventBus();

function getCookieCompanyIds() {
    if (cookie.get("cids")) {
        const cids = cookie.get("cids");
        if (typeof cids === "string") {
            return cids.split("-").map(Number);
        }
        if (typeof cids === "number") {
            return [cids];
        }
    }
    return [];
}

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
        is_public: isPublic,
        name,
        partner_id: partnerId,
        show_effect: showEffect,
        uid: userId,
        username: login,
        user_context: context,
        user_settings,
        partner_write_date: writeDate,
        user_companies: userCompanies,
        groups = {},
    } = session;
    const settings = user_settings || {};

    function updateActiveCompanies(cids, allowedCompanies, defaultCompanyId) {
        activeCompanies = [];
        cids.forEach((cid) => {
            activeCompanies.push(allowedCompanies.find((c) => c.id === cid));
        });
        if (
            activeCompanies.length === 0 ||
            activeCompanies.length !== activeCompanies.filter(Boolean).length
        ) {
            activeCompanies = [defaultCompanyId];
        }
        // Sort companies, except for the first one which has a different status, as the order of
        // the others doesn't matter, and we want to reduce the entropy of the `allowed_company_ids`
        // key in the context. This is important for the caches, as the stringified context is
        // always present in the rpc cache keys.
        activeCompanies = [activeCompanies[0]].concat(
            sortBy(activeCompanies.slice(1), (c) => c.id)
        );

        // update browser data
        cookie.set("cids", activeCompanies.map((c) => c.id).join("-"));
        Object.assign(context, { allowed_company_ids: activeCompanies.map((c) => c.id) });

        userBus.trigger("ACTIVE_COMPANIES_CHANGED");
    }

    // Companies information
    let allowedCompanies = [];
    const allowedCompaniesWithAncestors = [];
    let activeCompanies = [];
    let defaultCompany;

    if (userCompanies) {
        allowedCompanies = Object.values(userCompanies.allowed_companies);
        allowedCompaniesWithAncestors.push(...Object.values(userCompanies.allowed_companies));
        if (userCompanies.disallowed_ancestor_companies) {
            allowedCompaniesWithAncestors.push(
                ...Object.values(userCompanies.disallowed_ancestor_companies)
            );
        }
        defaultCompany = allowedCompanies.find((c) => c.id === userCompanies.current_company); // TODO: change the name in the session current_company to default_company
        updateActiveCompanies(getCookieCompanyIds(), allowedCompanies, defaultCompany);
    }

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
    delete session.user_companies;
    delete session.groups;

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
    if (isAdmin !== undefined) {
        groupCache.cache["base.group_erp_manager"] = Promise.resolve(isAdmin);
    }
    if (isPublic !== undefined) {
        groupCache.cache["base.group_public"] = Promise.resolve(isPublic);
    }
    for (const group in groups) {
        groupCache.cache[group] = Promise.resolve(!!groups[group]);
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

    return {
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
        updateUserSettings(key, value) {
            settings[key] = value;
        },
        defaultCompany, // default company of the user, used if no cookie set
        allowedCompanies, // list of authorized companies for the user
        allowedCompaniesWithAncestors,
        // list of companies the user is currently logged into
        get activeCompanies() {
            return activeCompanies;
        },
        // main company the user is currently logged into (default company for created records)
        get activeCompany() {
            return activeCompanies?.[0];
        },
        async activateCompanies(
            companyIds,
            options = { includeChildCompanies: true, reload: true }
        ) {
            const newCompanyIds = companyIds.length ? companyIds : [activeCompanies[0].id];

            function addCompanies(companyIds) {
                for (const companyId of companyIds) {
                    if (!newCompanyIds.includes(companyId)) {
                        newCompanyIds.push(companyId);
                        addCompanies(allowedCompanies.find((c) => c.id === companyId).child_ids);
                    }
                }
            }

            if (options.includeChildCompanies) {
                addCompanies(
                    companyIds.flatMap(
                        (companyId) => allowedCompanies.find((c) => c.id === companyId).child_ids
                    )
                );
            }

            updateActiveCompanies(newCompanyIds, allowedCompanies, defaultCompany);

            if (options.reload) {
                browser.location.reload();
            }
        },
    };
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
