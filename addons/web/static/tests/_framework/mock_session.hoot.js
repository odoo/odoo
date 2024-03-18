// ! WARNING: this module cannot depend on modules not ending with ".hoot" (except libs) !

import { serverState, onServerStateChange } from "./mock_server_state.hoot";

/**
 * @typedef {ReturnType<typeof _makeSession>} Session
 */

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export function mockSessionFactory() {
    return () => {
        const session = _makeSession(serverState);

        onServerStateChange(session, _makeSession);

        return { session };
    };
}

/**
 * @param {typeof serverState} serverState
 */
export function _makeSession({
    companies,
    lang,
    partnerId,
    partnerName,
    timezone,
    userContext,
    userId,
}) {
    return {
        active_ids_limit: 20000,
        bundle_params: {
            debug: new URLSearchParams(location.search).get("debug"),
            lang,
        },
        cache_hashes: {
            load_menus: "164b675eb9bf49f8bca52e350cd81482a8cf0d0c1c8a47d99bd063c0a0bf4f0d",
            translations: "f17c8e4bb0fd4d5db2615d28713486df97853a8f",
        },
        db: "test",
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
        server_version: "1.0",
        server_version_info: [1, 0, 0, "final", 0, ""],
        show_effect: true,
        uid: userId,
        // Commit: 3e847fc8f499c96b8f2d072ab19f35e105fd7749
        // to see what user_companies is
        user_companies: {
            allowed_companies: Object.fromEntries(
                companies.map((company) => [company.id, company])
            ),
            current_company: companies[0]?.id,
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
    };
}
