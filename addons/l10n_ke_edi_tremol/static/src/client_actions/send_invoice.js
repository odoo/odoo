/** @odoo-module **/

import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from "@web/core/registry";

async function postSend(env, action) {
    let refresh = false;
    const { orm, http, dialog, action: actionService } = env.services;

    for (const [move_id, invoice] of Object.entries([action.params.invoices])) {
        const result = JSON.parse(
            await http
                .post(invoice.proxy_address + "/hw_proxy/l10n_ke_cu_send", {
                    messages: invoice.messages,
                    company_vat: invoice.company_vat,
                })
                .catch((error) => {
                    dialog.add(AlertDialog, {
                        body:
                            env._t(
                                "Error trying to connect to the middleware. Is the middleware running?\n Error code: "
                            ) + error.status,
                    });
                })
        );
        if (result.status === "ok") {
            const { replies, serial_number } = result;
            orm.call("account.move", "l10n_ke_cu_response", [
                [],
                { replies, serial_number, move_id },
            ]).catch((error) => {
                dialog.add(AlertDialog, {
                    body:
                        env._t(
                            "Error trying to connect to Odoo. Check your internet connection.\n Error code: "
                        ) + error.status,
                });
            });
            refresh = true;
        } else {
            dialog.add(AlertDialog, {
                body: env._t("Posting an invoice has failed, with the message: \n") + result.status,
            });
        }
    }
    if (refresh) {
        actionService.doAction({
            type: "ir.actions.client",
            tag: "reload",
        });
    }
}

registry.category("actions").add("post_send", postSend);
