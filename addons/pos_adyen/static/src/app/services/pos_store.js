import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.data.connectWebSocket("ADYEN_LATEST_RESPONSE", async () => {
            const pendingLine = this.getPendingPaymentLine("adyen");

            if (pendingLine) {
                pendingLine.payment_method_id.payment_terminal.handleAdyenStatusResponse();
                return;
            }

            // No payment line is waiting for a result
            // avoid silently dropping a captured event
            for (const pm of this.config.payment_method_ids.filter(
                (m) => m.use_payment_terminal === "adyen"
            )) {
                await this._checkOrphanedAdyenNotification(pm);
            }
        });
    },

    async _checkOrphanedAdyenNotification(paymentMethod) {
        const notification = await this.data.silentCall(
            "pos.payment.method",
            "get_latest_adyen_status",
            [[paymentMethod.id]]
        );
        const saleToPOIResponse = notification?.SaleToPOIResponse;
        const response = saleToPOIResponse?.PaymentResponse?.Response;
        if (response?.Result !== "Success") {
            return;
        }

        // A notification can be replayed (e.g. bus reconnects)
        // Only alert if no local line at all knows about this service id.
        const serviceId = saleToPOIResponse.MessageHeader?.ServiceID;
        const alreadyKnown = this.models["pos.order"]
            .getAll()
            .some((order) =>
                order.payment_ids.some(
                    (line) =>
                        line.payment_method_id.id === paymentMethod.id &&
                        line.terminalServiceId === serviceId
                )
            );
        if (alreadyKnown) {
            return;
        }

        const pspReference = new URLSearchParams(response.AdditionalResponse).get("pspReference");
        logPosMessage(
            "PosAdyen",
            "_checkOrphanedAdyenNotification",
            "Adyen confirmed a payment that matches no payment line on this till",
            "#FF0000",
            [{ paymentMethodId: paymentMethod.id, serviceId, pspReference }],
            true
        );
        this.dialog.add(AlertDialog, {
            title: _t("Unmatched Adyen payment"),
            body: _t(
                "Adyen confirmed a payment (reference: %(ref)s) on terminal %(terminal)s that does not match any sale on this till. Do not assume it failed: check the Adyen back office before taking any action.",
                {
                    ref: pspReference || _t("unknown"),
                    terminal: paymentMethod.adyen_terminal_identifier,
                }
            ),
        });
    },
});
