/** @odoo-module **/

import { useState } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export function useKEProxy({onAllSent}) {
    onAllSent = onAllSent || (() => {});
    const state = useState({
        successfullySent: 0,
        error: false,
        message: "",
    });
    const orm = useService("orm");
    const http = useService("http");

    /**
     * Send each of the invoices provided to the proxy connected to the fiscal device. The proxy should return
     * details, from each successfully posted invoice, which are propagated back to the account move using the orm
     * service. Alternatively, the proxy can return an error, in which case the execution of this function should
     * halt, though the successfully posted invoices are still updated as above.
     *
     * @param Array<Object> invoices array representing serialised invoice data and the proxy address to send each invoice to.
     */
    async function postInvoices(invoices) {

        // Ping the server to prevent posting to the device when there is no connection to the odoo server
        try {
            await rpc("/web/webclient/version_info", {});
        } catch (e) {
            // Allow the default error handler to execute after displaying an error message in the dialog
            state.message = _t("Connection lost, please try again later.");
            state.error = true;
            throw e;
        }
        let progress; // keep track of when an error occurs
        for (const index in invoices) {
            let { move_id, messages, proxy_address, company_vat, name } = invoices[index];
            state.message = _t("Posting invoice: %s", name);
            try {
                progress = 'postToDevice';
                let deviceResponse = await http.post(
                    proxy_address + '/hw_proxy/l10n_ke_cu_send', {
                        messages: messages,
                        company_vat: company_vat,
                    },
                );
                progress = 'parseResponse';
                if (deviceResponse.status === "ok") {
                    progress = 'updateInvoice'
                    deviceResponse.move_id = move_id;
                    await orm.call("account.move", "l10n_ke_cu_responses", [[], [deviceResponse]]);
                    state.successfullySent++;
                } else {
                    throw new Error(deviceResponse.status)
                }
            } catch (e) {
                state.error = true;
                switch (progress) {
                    case 'postToDevice':
                        state.message = _t("Error trying to connect to the middleware. Is the middleware running? \n Error message: %s", e.message);
                        break;
                    case 'parseResponse':
                        state.message = _t("Posting the invoice %s has failed with the message: \n %s", name, e.message);
                        break;
                    case 'updateInvoice':
                        state.message = _t("Error trying to connect to Odoo. Check your internet connection. Error message: %s", e.message);
                        break;
                    default:
                        state.message = _t("Unexpected Error:\n %s", e.message);
                }
                break;
            }
        }
        if (state.successfullySent == invoices.length) {
            onAllSent();
        }
    }

    return {
        postInvoices,
        state,
    };
}
