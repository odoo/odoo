// @ts-check

import { EventBus } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { cookie } from "@web/core/browser/cookie";
import { pyToJsLocale } from "@web/core/l10n/utils";
import { rpc } from "@web/core/network/rpc";
import { ensureArray, sortBy } from "@web/core/utils/collections/arrays";
import { Cache } from "@web/core/utils/collections/cache";
import { session } from "@web/session";

/**
 * User identity, company context, group membership, and access-right checks.
 * Exports a singleton `user` object constructed from the session, along with
 * a `userBus` that emits `ACTIVE_COMPANIES_CHANGED` on company switches.
 * @module user
 */

/**
 * @typedef {Object} UserObject
 * @property {string} name - display name
 * @property {string} login - username / email
 * @property {boolean} isAdmin - is ERP manager
 * @property {boolean} isSystem - has system group
 * @property {boolean} isInternalUser - has internal user group
 * @property {number} partnerId - res.partner ID
 * @property {number|false} homeActionId - default home action
 * @property {boolean} showEffect - whether to show UI effects (confetti, etc.)
 * @property {number} userId - res.users ID
 * @property {string} writeDate - partner write date (for avatar cache busting)
 * @property {Object} context - user context (lang, tz, uid, allowed_company_ids)
 * @property {string} lang - BCP 47 locale string
 * @property {string} tz - timezone identifier
 * @property {Object} settings - res.users.settings snapshot
 * @property {(update: Object) => void} updateContext - merge keys into the user context
 * @property {(group: string) => Promise<boolean>} hasGroup - check group membership (cached)
 * @property {(model: string, operation: string, ids?: number[]) => Promise<boolean>} checkAccessRight - check model ACL (cached)
 * @property {(key: string, value: any) => Promise<void>} setUserSettings - persist a setting to the server
 * @property {(key: string, value: any) => void} updateUserSettings - update a setting locally (no RPC)
 * @property {{id: number} | undefined} defaultCompany - fallback company from session
 * @property {Array<{id: number, child_ids: number[]}>} allowedCompanies - authorized companies
 * @property {Array<{id: number}>} allowedCompaniesWithAncestors - includes disallowed ancestors
 * @property {Array<{id: number}>} activeCompanies - currently selected companies
 * @property {{id: number, currency_id: number}} activeCompany - primary active company
 * @property {(companyIds: number[], options?: {includeChildCompanies?: boolean, reload?: boolean}) => Promise<void>} activateCompanies - switch active companies
 */

export const userBus = new EventBus();

/** @returns {number[]} */
function getCookieCompanyIds() {
    const cids = cookie.get("cids");
    if (typeof cids === "string") {
        return cids.split("-").map(Number);
    }
    if (typeof cids === "number") {
        return [cids];
    }
    return [];
}

/**
 * Build the user object from session data. Exposed for testing so each test
 * suite can construct an isolated instance with fresh caches.
 *
 * @param {Record<string, any>} session - the raw session payload from the server
 * @returns {UserObject} the user singleton with identity, companies, and access APIs
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

    /**
     * Update the list of active companies from cookie IDs, falling back to
     * the default company if the cookie values are stale or empty.
     * @param {number[]} cids - company IDs from the cookie
     * @param {Array<{id: number, child_ids: number[]}>} allowedCompanies
     * @param {{id: number} | undefined} defaultCompany
     */
    function updateActiveCompanies(cids, allowedCompanies, defaultCompany) {
        activeCompanies = [];
        cids.forEach((cid) => {
            activeCompanies.push(allowedCompanies.find((c) => c.id === cid));
        });
        if (
            activeCompanies.length === 0 ||
            activeCompanies.length !== activeCompanies.filter(Boolean).length
        ) {
            // Fall back to the default company, or the first allowed company if
            // the default is undefined (e.g. session current_company not found
            // in the allowed list). Guard against both being absent so the
            // subsequent .map((c) => c.id) never receives undefined elements.
            const fallback = defaultCompany || allowedCompanies[0];
            activeCompanies = fallback ? [fallback] : [];
        }
        // Sort companies, except for the first one which has a different status, as the order of
        // the others doesn't matter, and we want to reduce the entropy of the `allowed_company_ids`
        // key in the context. This is important for the caches, as the stringified context is
        // always present in the rpc cache keys.
        if (activeCompanies.length > 0) {
            activeCompanies = [
                activeCompanies[0],
                ...sortBy(activeCompanies.slice(1), (c) => c.id),
            ];
        }

        // update browser data
        cookie.set("cids", activeCompanies.map((c) => c.id).join("-"));
        Object.assign(context, {
            allowed_company_ids: activeCompanies.map((c) => c.id),
        });

        userBus.trigger("ACTIVE_COMPANIES_CHANGED");
    }

    // Companies information
    let allowedCompanies = [];
    const allowedCompaniesWithAncestors = [];
    let activeCompanies = [];
    let defaultCompany;

    if (userCompanies) {
        allowedCompanies = Object.values(userCompanies.allowed_companies);
        allowedCompaniesWithAncestors.push(
            ...Object.values(userCompanies.allowed_companies),
        );
        if (userCompanies.disallowed_ancestor_companies) {
            allowedCompaniesWithAncestors.push(
                ...Object.values(userCompanies.disallowed_ancestor_companies),
            );
        }
        defaultCompany = allowedCompanies.find(
            (c) => c.id === userCompanies.current_company,
        ); // TODO: change the name in the session current_company to default_company
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
    /** @type {(group: string, context: Object) => Promise<boolean>} */
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
    for (const [group, value] of Object.entries(groups)) {
        groupCache.cache[group] = Promise.resolve(!!value);
    }
    /** @type {(model: string, operation: string, ids: number[], context: Object) => Promise<boolean>} */
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
    const accessRightCache = new Cache(
        getAccessRightCacheValue,
        getAccessRightCacheKey,
    );
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
            return { ...context, uid: this.userId };
        },
        get lang() {
            return lang;
        },
        get tz() {
            return this.context.tz;
        },
        get settings() {
            return { ...settings };
        },
        updateContext(update) {
            Object.assign(context, update);
        },
        hasGroup(group) {
            return groupCache.read(group, this.context);
        },
        checkAccessRight(model, operation, ids = []) {
            return accessRightCache.read(
                model,
                operation,
                ensureArray(ids),
                this.context,
            );
        },
        async setUserSettings(key, value) {
            const model = "res.users.settings";
            const method = "set_res_users_settings";
            const changedSettings = await rpc(
                `/web/dataset/call_kw/${model}/${method}`,
                {
                    model,
                    method,
                    args: [[this.settings.id]],
                    kwargs: {
                        new_settings: {
                            [key]: value,
                        },
                        context: this.context,
                    },
                },
            );
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
            options = { includeChildCompanies: true, reload: true },
        ) {
            // Fall back to the current primary company when no ids are given.
            // Guard activeCompanies[0] against the (degenerate) no-company case.
            const newCompanyIds = companyIds.length
                ? companyIds
                : activeCompanies[0]
                  ? [activeCompanies[0].id]
                  : [];

            function addCompanies(companyIds) {
                for (const companyId of companyIds) {
                    if (!newCompanyIds.includes(companyId)) {
                        newCompanyIds.push(companyId);
                        // A child_id might not be in allowedCompanies (e.g. the
                        // user has no access to it). Skip rather than crash.
                        const company = allowedCompanies.find(
                            (c) => c.id === companyId,
                        );
                        if (company) {
                            addCompanies(company.child_ids);
                        }
                    }
                }
            }

            if (options.includeChildCompanies) {
                addCompanies(
                    companyIds.flatMap((companyId) => {
                        const company = allowedCompanies.find(
                            (c) => c.id === companyId,
                        );
                        return company ? company.child_ids : [];
                    }),
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

/** @returns {any[]} */
export const getLastConnectedUsers = () => {
    const lastConnectedUsers = browser.localStorage.getItem(LAST_CONNECTED_USER_KEY);
    return lastConnectedUsers ? JSON.parse(lastConnectedUsers) : [];
};

/** @param {any[]} users */
export const setLastConnectedUsers = (users) => {
    browser.localStorage.setItem(
        LAST_CONNECTED_USER_KEY,
        JSON.stringify(users.slice(0, 5)),
    );
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
