/** @odoo-module */

import { before } from "@odoo/hoot";

/**
 * @typedef {typeof sessionValue} Session
 */

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

// Config constants
const COMPANY_ID = 1;
const COMPANY_NAME = "Hermit";
const GROUP_ID = 11;
const LANG = "en";
const ODOOBOT_ID = 418;
const PARTNER_ID = 17;
const PARTNER_NAME = "Mitchell Admin";
const PUBLIC_PARTNER_ID = 18;
const PUBLIC_PARTNER_NAME = "Public user";
const PUBLIC_USER_ID = 8;
const USER_ID = 7;

/** Actual session object */
const sessionValue = {
    active_ids_limit: 20000,
    bundle_params: {
        debug: new URLSearchParams(location.search).get("debug"),
        lang: LANG,
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
    name: PARTNER_NAME,
    partner_display_name: PARTNER_NAME,
    partner_id: PARTNER_ID,
    profile_collectors: null,
    profile_params: null,
    profile_session: null,
    server_version: "1.0",
    server_version_info: [1, 0, 0, "final", 0, ""],
    show_effect: true,
    uid: USER_ID,
    // Commit: 3e847fc8f499c96b8f2d072ab19f35e105fd7749
    // to see what user_companies is
    user_companies: {
        allowed_companies: { [COMPANY_ID]: { id: COMPANY_ID, name: COMPANY_NAME } },
        current_company: COMPANY_ID,
    },
    user_context: {
        lang: LANG,
        tz: "taht",
        uid: USER_ID,
    },
    user_id: [USER_ID],
    username: "admin",
    ["web.base.url"]: "http://localhost:8069",
    // << not in the actual session, but useful for tests
    group_id: GROUP_ID,
    odoobot_id: ODOOBOT_ID,
    public_partner_id: PUBLIC_PARTNER_ID,
    public_partner_display_name: PUBLIC_PARTNER_NAME,
    public_user_id: PUBLIC_USER_ID,
    public_user_name: PUBLIC_PARTNER_NAME,
    // >>
};

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * @param {Partial<Session> | (session: Session) => Partial<Session>} getSession
 */
export function mockSession(getSession) {
    before(() => {
        Object.assign(
            sessionValue,
            typeof getSession === "function" ? getSession(sessionValue) : getSession
        );
    });
}

export function mockSessionFactory() {
    return () => ({
        get session() {
            return { ...sessionValue };
        },
    });
}
