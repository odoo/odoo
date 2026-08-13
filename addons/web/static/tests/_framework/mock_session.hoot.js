// ! WARNING: this module cannot depend on modules not ending with ".hoot" (except libs) !

import { onServerStateChange, serverState } from "./mock_server_state.hoot";

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {typeof serverState} serverState
 */
const makeSession = ({
    companies,
    db,
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
    },
    cache_hashes: {
        load_menus: "164b675eb9bf49f8bca52e350cd81482a8cf0d0c1c8a47d99bd063c0a0bf4f0d",
        translations: "f17c8e4bb0fd4d5db2615d28713486df97853a8f",
    },
    can_insert_in_spreadsheet: true,
    db,
    display_switch_company_menu: false,
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
    // Commit: 3e847fc8f499c96b8f2d072ab19f35e105fd7749
    // to see what user_companies is
    user_companies: {
        allowed_companies: Object.fromEntries(companies.map((company) => [company.id, company])),
        current_company: companies[0]?.id,
        disallowed_ancestor_companies: {},
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
});

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export function mockSessionFactory() {
    return () => {
        const session = makeSession(serverState);

        onServerStateChange(session, makeSession);

        return { session };
    };
}
