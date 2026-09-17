/** @odoo-module native */
import { makeLogger } from "@web/core/debug/debug_logger";
import { registry } from "@web/core/registry";

const log = makeLogger("account.return");

export async function AccountReturnCloseWizard(env, action) {
    const nextAction = action.params?.next_action;
    log.lifecycle("closeWizard", () => ({ nextAction: nextAction?.type || null }));
    return nextAction || { type: "ir.actions.act_window_close" };
}

registry
    .category("actions")
    .add("action_return_close_wizard", AccountReturnCloseWizard);
