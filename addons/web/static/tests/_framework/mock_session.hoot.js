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
    can_insert_in_spreadsheet: true,
    db,
    registry_hash: "05500d71e084497829aa807e3caa2e7e9782ff702c15b2f57f87f2d64d049bd0",
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
