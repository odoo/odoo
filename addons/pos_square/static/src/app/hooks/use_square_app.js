import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";
import { isIOS } from "@web/core/browser/feature_detection";
import { roundPrecision } from "@web/core/utils/numbers";
import { _t } from "@web/core/l10n/translation";

const PLAY_STORE_URL = "https://play.google.com/store/apps/details?id=com.squareup";
// Android has no gift card tender.
const IOS_TENDER_TYPES = ["CASH", "OTHER", "SQUARE_GIFT_CARD", "CARD_ON_FILE"];
const ANDROID_TENDER_TYPES = ["TENDER_CASH", "TENDER_OTHER", "TENDER_CARD_ON_FILE"];

const PAYMENT_FAILED = _t(
    "Please note that your order has not been finalized, try again or choose another payment method."
);

// iOS only returns an error code, so spell out the ones the cashier can act on.
const IOS_ERRORS = {
    could_not_perform: _t(
        "A transaction is still pending in the Square app; complete it there before starting a new one."
    ),
    currency_code_mismatch: _t("This currency doesn't match the one of the Square account."),
    no_network_connection: _t("The device has no network connection."),
    not_logged_in: _t("No seller is logged in to the Square app."),
    payment_canceled: _t("The payment was cancelled in the Square app."),
    user_not_active: _t("The Square account isn't activated for card processing."),
};

// Square PoS API: https://developer.squareup.com/docs/pos-api/web-technical-reference
export const useSquareApp = () => {
    const pos = usePos();
    const dialog = useService("dialog");
    const showError = (body) =>
        dialog.add(AlertDialog, { title: _t("Square Payment Error"), body });

    /** Build the URL that opens the Square app on its charge screen. */
    const buildUrl = (line) => {
        const order = line.pos_order_id;
        const applicationId = line.payment_method_id.square_application_id;
        const amount = roundPrecision(Math.abs(line.amount) * 100); // in the smallest currency unit
        const callbackUrl = `${window.location.origin}/pos_square/callback`;
        const state = `${order.uuid}|${line.uuid}`;

        if (isIOS()) {
            const data = {
                amount_money: { amount: amount, currency_code: pos.currency.name },
                callback_url: callbackUrl,
                client_id: applicationId,
                state: state,
                version: "1.3",
                notes: order.pos_reference,
                auto_return: true,
                skip_receipt: true,
                clear_default_fees: true,
                options: { supported_tender_types: IOS_TENDER_TYPES },
            };
            return `square-commerce-v1://payment/create?data=${encodeURIComponent(
                JSON.stringify(data)
            )}`;
        }

        // browser_fallback_url is what Android opens when the Square app isn't installed.
        return [
            "intent:#Intent",
            "action=com.squareup.pos.action.CHARGE",
            "package=com.squareup",
            `S.browser_fallback_url=${encodeURIComponent(PLAY_STORE_URL)}`,
            `S.com.squareup.pos.WEB_CALLBACK_URI=${callbackUrl}`,
            `S.com.squareup.pos.CLIENT_ID=${applicationId}`,
            "S.com.squareup.pos.API_VERSION=v2.0",
            "l.com.squareup.pos.AUTO_RETURN_TIMEOUT_MS=3200",
            `i.com.squareup.pos.TOTAL_AMOUNT=${amount}`,
            `S.com.squareup.pos.CURRENCY_CODE=${pos.currency.name}`,
            `S.com.squareup.pos.TENDER_TYPES=${ANDROID_TENDER_TYPES.map(
                (type) => `com.squareup.pos.${type}`
            ).join(",")}`,
            `S.com.squareup.pos.REQUEST_METADATA=${state}`,
            // The receipt number is free text, and `;` delimits the intent parameters.
            `S.com.squareup.pos.NOTE=${encodeURIComponent(order.pos_reference || "")}`,
            "end",
        ].join(";");
    };

    /** Add the payment line and open the Square app on it. */
    const start = async (paymentMethod) => {
        const order = pos.getOrder();
        const result = order.addPaymentline(paymentMethod);
        if (!result.status) {
            showError(result.data);
            return;
        }

        const line = result.data;
        try {
            // The callback updates the order server side while the PoS is gone.
            const synced = await pos.syncAllOrders({ orders: [order] });
            await pos.data.synchronizeLocalDataInIndexedDB();
            if (!synced) {
                throw new Error("the order must be synced before opening the Square app");
            }
            line.setPaymentStatus("waitingCard");
            window.open(buildUrl(line), "_self");
        } catch {
            order.removePaymentline(line);
            showError(PAYMENT_FAILED);
        }
    };

    /** Apply the outcome the callback put in the URL onto the local payment line. */
    const process = async () => {
        const urlParams = new URLSearchParams(window.location.search);
        const status = urlParams.get("square_status");
        if (!status) {
            return;
        }

        await pos.syncAllOrders({ orders: [pos.getOrder()] });
        const order = pos.getOrder();
        const line = order.getPaymentlineByUuid(urlParams.get("square_payment"));

        if (status === "success") {
            line?.setPaymentStatus("done");
        } else {
            const message = urlParams.get("square_message");
            if (line) {
                order.removePaymentline(line);
            }
            showError(`${PAYMENT_FAILED} (${IOS_ERRORS[message] || message})`);
        }

        // Remove the URL parameters to avoid processing them again
        window.history.replaceState({}, document.title, window.location.href.split("?")[0]);
    };

    return { start, process };
};
