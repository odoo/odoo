// @ts-check

import { onServerStateChange, serverState } from "./mock_server_state.hoot.js";

const moduleScope = new URLSearchParams(location.search).get("module_scope");

/**
 * Mirror of `ir.http.session_info()["groups"]`: `web` seeds
 * `base.group_allow_export`; an addon whose `ir.http` override adds a group
 * registers it here from its test helpers, so a mock session seeds
 * `user.hasGroup` exactly as a real one does and a service that reads those
 * groups at boot makes no RPC in a test either.
 *
 * @type {Map<string, boolean>}
 */
const sessionGroups = new Map([["base.group_allow_export", true]]);

/** @param {Record<string, boolean>} groups */
export function registerSessionGroups(groups) {
    for (const [group, value] of Object.entries(groups)) {
        sessionGroups.set(group, value);
    }
}

/**
 * Mirror of an addon's `ir.http.session_info()` override for the keys it
 * owns: registered from the addon's test helpers at load, merged last into
 * every mock session, so the session a suite boots with says what the
 * server says on a database where that addon is installed.
 *
 * @type {Record<string, unknown>}
 */
const sessionExtensions = {};

/** @param {Record<string, unknown>} extension */
export function registerSessionInfo(extension) {
    Object.assign(sessionExtensions, extension);
}

/** @param {typeof serverState} serverState */
export const makeSession = ({
    companies,
    db,
    disallowedAncestorCompanies,
    lang,
    partnerId,
    partnerName,
    serverVersion,
    timezone,
    userContext,
    userId,
    view_info,
}) => ({
    active_ids_limit: 20000,
    bundle_params: {
        debug: new URLSearchParams(location.search).get("debug"),
        lang,
        ...(moduleScope ? { module_scope: moduleScope } : {}),
    },
    can_insert_in_spreadsheet: false,
    db,
    registry_hash: "05500d71e084497829aa807e3caa2e7e9782ff702c15b2f57f87f2d64d049bd0",
    menus_cache_version: `05500d71e084497829aa807e3caa2e7e9782ff702c15b2f57f87f2d64d049bd0:${userId}`,
    groups: Object.fromEntries(sessionGroups),
    home_action_id: false,
    is_admin: true,
    is_internal_user: true,
    is_system: true,
    max_file_upload_size: 134217728,
    name: partnerName,
    partner_display_name: partnerName,
    partner_id: partnerId,
    profile_collectors: null,
    profile_params: null,
    profile_session: null,
    server_version: serverVersion.slice(0, 2).join("."),
    server_version_info: serverVersion,
    show_effect: true,
    uid: userId,
    user_companies: {
        allowed_companies: Object.fromEntries(
            companies.map((company) => [company.id, company]),
        ),
        current_company: companies[0]?.id,
        disallowed_ancestor_companies: Object.fromEntries(
            (disallowedAncestorCompanies || []).map((company) => [company.id, company]),
        ),
    },
    user_context: {
        ...userContext,
        lang,
        tz: timezone,
        uid: userId,
    },
    user_id: [userId],
    username: "admin",
    ["web.base.url"]: "http://localhost:8069",
    view_info,
    ...sessionExtensions,
});

export function mockSessionFactory() {
    return () => {
        const session = makeSession(serverState);

        onServerStateChange(session, makeSession);

        return { session };
    };
}
