import { registry } from "@web/core/registry"


export async function PeppolAuthCallbackAction(env, action) {
    const params = action.params || {};
    if (window.opener && window.opener.odoo) {
        // if the current window has been opened by odoo, we can close it
        window.close();
    }
    return params.next;
}

registry.category("actions").add("action_peppol_auth_callback", PeppolAuthCallbackAction)
