/** @odoo-module **/

import { registry } from "@web/core/registry";
import { KEProxyDialog } from "./ke_proxy_dialog";

export function KESendInvoiceClientAction(env, action) {
    return new Promise((resolve) => {
        env.services.dialog.add(
            KEProxyDialog,
            {
                invoices: action.params,
            },
            {
                onClose: () => {
                    resolve({ type: "ir.actions.act_window_close" });
                },
            }
        );
    });
}

registry.category("actions").add("l10n_ke_post_send", KESendInvoiceClientAction);
