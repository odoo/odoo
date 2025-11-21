import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";
import { roundPrecision } from "@web/core/utils/numbers";
import { _t } from "@web/core/l10n/translation";
import { uuidv4 } from "@point_of_sale/utils";

/**
 * This hook is used to handle the Viva Wallet app integration in the POS.
 * API documentation: https://developer.viva.com/apis-for-point-of-sale/card-terminal-apps/android-app/sale/
 */
export const useVivaApp = (validateCallback) => {
    const pos = usePos();
    const dialog = useService("dialog");
    const order = pos.getOrder();

    /**
     * This function determines if the payment method is a Viva Wallet and
     * if the device should use the Viva Wallet app to process the payment.
     *
     * @param {Object} pm - The payment method object.
     */
    const use = (pm) => {
        const isAndroid = navigator.userAgent.toLowerCase().includes("android");
        return isAndroid && pm.use_payment_terminal === "viva_com";
    };

    /**
     * Since we have a new router, the vivawallet callback URL will directly
     * target the receipt screen, so we need to check if the URL contains
     * the result of the payment and if it does, we need to process it
     * and update the payment line accordingly.
     */
    const process = async () => {
        const urlParams = new URLSearchParams(window.location.search);
        const status = urlParams.get("status");
        const action = urlParams.get("action");
        const ref = urlParams.get("referenceNumber");
        const bankId = urlParams.get("bankId");

        if (!action || !status) {
            return;
        }

        const order = pos.getOrder();
        await pos.syncAllOrders({ orders: [order] });
        const line = pos
            .getOrder()
            .payment_ids.find((l) => l.payment_method_id.use_payment_terminal === "viva_com");

        if (status === "success") {
            line.payment_status = "done";
            line.transaction_id = ref;
            line.card_type = bankId;
            await validateCallback(true);
        } else {
            // Used identifier is clientTransactionId which is sent during payment initiation
            // If status is not success, the error message will be returned via message field
            const message = urlParams.get("message");
            line?.delete();
            dialog.add(AlertDialog, {
                title: _t("Viva Wallet Payment Error"),
                body: `Please note that your order has not been finalized, try again or choose another payment method. (${message})`,
            });
        }

        // Remove the URL parameters to avoid processing them again
        const newUrl = window.location.href.split("?")[0];
        window.history.replaceState({}, document.title, newUrl);
    };

    /**
     * This function is used to open the Viva Wallet app
     * and start the payment process. It will open the app with the
     * necessary parameters to process the payment.
     *
     * @param {Object} paymentMethod
     * @param {Boolean} isRefund
     */
    const start = async (paymentMethod, isRefund = false) => {
        const line = order.addPaymentline(paymentMethod);
        try {
            line.viva_com_session_id = `${order.uuid}-${uuidv4()}`;
            const result = await pos.syncAllOrders({ orders: [order] });
            await pos.data.synchronizeLocalDataInIndexedDB();
            if (!result) {
                throw new Error(
                    "Impossible to initiate Vivawallet payment without syncing the order"
                );
            }

            let url =
                "vivapayclient://pay/v1" +
                "?appId=com.example.odoo" + // We don't have a real appId, so we use a dummy one
                `&amount=${roundPrecision(Math.abs(line.amount * 100))}` +
                "&show_receipt=true" +
                "&show_transaction_result=true" +
                "&show_rating=true" +
                `&callback=${pos.session._base_url}/pos/ui/${pos.config.id}/payment/${order.uuid}`;

            if (isRefund) {
                const refundedOrderPay = line.pos_order_id.refunded_order_id.payment_ids;
                const vivaLine = refundedOrderPay.find(
                    (p) => p.payment_method_id.use_payment_terminal === "viva_com"
                );

                if (vivaLine) {
                    url += `&referenceNumber=${vivaLine.transaction_id}`;
                }

                url += `&action=cancel`;
            } else {
                url += `&action=sale`;
                url += `&clientTransactionId=${line.viva_com_session_id}`;
                url += `&ISV_currencyCode=${pos.currency.iso_numeric.toString()}`;
                url += `&ISV_merchantId=${line.viva_com_session_id}/${pos.session.id}`;
                url += `&tipAmount=0`;
                url += `&paymentMethod=CardPresent`;

                if (order.partner) {
                    url += `&ISV_customerTrns=${order.partner.name}-${order.partner.email}`;
                }
            }

            line.setPaymentStatus("waitingCard");
            window.open(url, "_self");
        } catch {
            line.delete();
            dialog.add(AlertDialog, {
                title: _t("Viva Wallet Payment Error"),
                body: _t(
                    "Please note that your order has not been finalized, try again or choose another payment method."
                ),
            });
        }
    };

    return {
        use,
        process,
        start,
    };
};
