import { registry } from "@web/core/registry";
import { KEProxyDialog } from "./ke_proxy_dialog";
import { useService } from "@web/core/utils/hooks";

export function KESendInvoiceClientAction(env, action) {
    const dialog = useService("dialog");
    return new Promise((resolve) => {
        dialog.add(
            KEProxyDialog,
            { invoices: action.params },
            {
                onClose: () => {
                    resolve({ type: "ir.actions.act_window_close" });
                },
            }
        );
    });
}

registry.category("actions").add("l10n_ke_post_send", KESendInvoiceClientAction);
