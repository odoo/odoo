// ! WARNING: this module cannot depend on modules not ending with ".hoot" (except libs) !

import { constants } from "./test_constants.hoot";

/**
 * @typedef {typeof SESSION} Session
 */

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

const SESSION = Object.freeze({
    active_ids_limit: 20000,
    bundle_params: {
        debug: new URLSearchParams(location.search).get("debug"),
        lang: constants.LANG,
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
    name: constants.PARTNER_NAME,
    partner_display_name: constants.PARTNER_NAME,
    partner_id: constants.PARTNER_ID,
    profile_collectors: null,
    profile_params: null,
    profile_session: null,
    server_version: "1.0",
    server_version_info: [1, 0, 0, "final", 0, ""],
    show_effect: true,
    uid: constants.USER_ID,
    // Commit: 3e847fc8f499c96b8f2d072ab19f35e105fd7749
    // to see what user_companies is
    user_companies: {
        allowed_companies: {
            [constants.COMPANY_ID]: {
                id: constants.COMPANY_ID,
                name: constants.COMPANY_NAME,
            },
        },
        current_company: constants.COMPANY_ID,
    },
    user_context: {
        lang: constants.LANG,
        tz: constants.TIMEZONE,
        uid: constants.USER_ID,
    },
    user_id: [constants.USER_ID],
    username: "admin",
    ["web.base.url"]: "http://localhost:8069",
});

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export function mockSessionFactory() {
    const currentSession = JSON.parse(JSON.stringify(SESSION));
    return () => ({
        get session() {
            return currentSession;
        },
    });
}
