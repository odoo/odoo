import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { PrintLabel } from "./label/label";

async function printer(env, action) {
    if (!action.params.ip_printers.length) {
        env.services.dialog.add(ConfirmationDialog, {
            title: _t("Printer Configuration Required"),
            body: _t(
                "You cannot print labels without specifying the IP address of the EPSON Label Printer."
            ),
            confirmLabel: _t("Configure Printer"),
            cancelLabel: _t("Cancel"),
            confirm: async () => {
                await env.services.action.doAction({
                    type: "ir.actions.act_window",
                    name: _t("Configure EPSON Label Printer"),
                    res_model: "ir.actions.report",
                    res_id: action.params.report_id,
                    views: [[false, "form"]],
                    target: "new",
                });
            },
            cancel: () => {
                action.params.next;
            },
        });
        return;
    }

    action.params.ip_printers.forEach(async (ip) => {
        for (const product of action.params.products) {
            let cnt = 0;
            while (cnt < action.params.quantity) {
                await env.services.label_printer.print(
                    PrintLabel,
                    {
                        product: product,
                    },
                    {},
                    ip
                );
                cnt++;
            }
        }
    });
    return action.params.next;
}

registry.category("actions").add("epson_label_action", (env, action) => printer(env, action));
