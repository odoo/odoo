/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

export async function downloadAndCloseFollowupWizardAction(env, action) {
    const url = action.params.url
    try {
        browser.open(url);
    }
    finally {
        return { type: "ir.actions.act_window_close" };
    }
}

registry.category("actions").add("close_followup_wizard", downloadAndCloseFollowupWizardAction);
