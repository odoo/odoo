import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { isIOS, isAndroid } from "@web/core/browser/feature_detection";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { roundPrecision } from "@web/core/utils/numbers";
import { registry } from "@web/core/registry";

export class PaymentSquare extends PaymentInterface {
    /*
     Developer documentation:
    https://developer.squareup.com/docs/pos-api/web-technical-reference
    */
    setup() {
        super.setup(...arguments);
        this.paymentLineResolvers = {};
        this.isIOS = isIOS();
        this.isAndroid = isAndroid();
        this.supports_reversals = false; // Square doesn't support automatic reversals via POS API
    }
    async sendPaymentRequest(uuid) {
        /**
         * Override
         */
        // if (!this.isIos && !this.isAndroid) {
        //     this._showError(_t("Square payment method is only available on iOS and Android devices."));
        // }
        const line = this.pos.getOrder().getSelectedPaymentline();
        line.setPaymentStatus("waitingCapture");
        // URL Must be opened immediately after a user interaction (e.g., button click),
        // IOS and Android block popups opened asynchronously
        // const win = window.open("", "_blank");
        const payload = this._buildPayload(line);
        window.open(`/pos_square/callback?is_ios=${this.isIOS}&payload=${payload}`);
        await super.sendPaymentRequest(...arguments);
        line.setPaymentStatus("waitingCard");
        // Wait for payment intent status change and return status result
        return this.waitForPaymentConfirmation(uuid);
    }

    waitForPaymentConfirmation(uuid) {
        return new Promise((resolve) => {
            this.paymentLineResolvers[uuid] = resolve;
        });
    }

    sendPaymentCancel(order, uuid) {
        super.sendPaymentCancel(order, uuid);
        return true;
    }

    _buildPayload(line) {
        const callbackUrl = `${window.location.origin}/pos_square/callback`;
        const applicationId = this.payment_method_id.square_application_id;
        const transactionTotal = roundPrecision(line.amount * 100, 0); // in cents
        const currencyCode = this.pos.currency.name;
        const tenderTypes = ["CASH", "OTHER", "SQUARE_GIFT_CARD", "CARD_ON_FILE"];
        const orderRef = this.pos.getOrder().pos_reference;
        const stateParameter = encodeURIComponent(
            `${this.pos.session.id}|${this.pos.getOrder().id}|${this.payment_method_id.id}|${
                line.id
            }`
        );
        let payload;
        if (this.isIOS) {
            payload = encodeURIComponent(
                JSON.stringify({
                    amount_money: { amount: transactionTotal, currency_code: currencyCode },
                    callback_url: callbackUrl,
                    client_id: applicationId,
                    state: stateParameter,
                    version: "1.3",
                    notes: orderRef,
                    auto_return: true,
                    skip_receipt: true,
                    clear_default_fees: true,
                    options: { supported_tender_types: tenderTypes },
                })
            );
        } else {
            const androidTenderTypes = tenderTypes
                .map((type) => `com.squareup.pos.TENDER_${type}`)
                .join(",");
            const payloadParameters = [
                "action=com.squareup.pos.action.CHARGE",
                "package=com.squareup",
                `S.com.squareup.pos.WEB_CALLBACK_URI=${callbackUrl}`,
                `S.com.squareup.pos.CLIENT_ID=${applicationId}`,
                "S.com.squareup.pos.API_VERSION=v2.0",
                "l.com.squareup.pos.AUTO_RETURN_TIMEOUT_MS=3200",
                `i.com.squareup.pos.TOTAL_AMOUNT=${transactionTotal}`,
                `S.com.squareup.pos.CURRENCY_CODE=${currencyCode}`,
                `S.com.squareup.pos.TENDER_TYPES=${androidTenderTypes}`,
                `S.com.squareup.pos.REQUEST_METADATA=${stateParameter}`,
                `S.com.squareup.pos.NOTE=${orderRef}`,
            ];
            payload = payloadParameters.join(";");
        }
        return payload;
    }

    /**
     * This method is called from pos_bus when the payment
     * confirmation from Square is received.
     */
    async handleSquareStatusResponse(data) {
        const line = this.pendingSquareLine;
        const notification = data.response;
        if (!line || line.uuid !== data.line_uuid) {
            console.warn(
                "Square response received for a line that is not pending or does not match the current line."
            );
            return;
        }
        const isPaymentSuccessful = !("error_code" in notification);
        if (isPaymentSuccessful) {
            line.transaction_id = notification.transaction_id;
        } else {
            this._showError(
                notification.error_description ??
                    this._getSquarePOSErrorMessage(notification.error_code)
            );
        }
        // when starting to wait for the payment response we create a promise
        // that will be resolved when the payment response is received.
        // In case this resolver is lost ( for example on a refresh )
        // we use the handlePaymentResponse method on the payment line
        const resolver = this.paymentLineResolvers?.[line.uuid];
        if (resolver) {
            resolver(isPaymentSuccessful);
        } else {
            line.handlePaymentResponse(isPaymentSuccessful);
        }
    }

    get pendingSquareLine() {
        return this.pos.getPendingPaymentLine("square");
    }

    _showError(msg, title) {
        if (!title) {
            title = _t("Square Error");
        }
        this.env.services.dialog.add(AlertDialog, {
            title: title,
            body: msg,
        });
    }

    /**
     * Get error description for Square Point of Sale API error codes
     * @param {string} code - The error code from iOS or Android
     * @returns {string} - The error description
     */
    _getSquarePOSErrorMessage(code) {
        const squareErrors = {
            // IOS Errors
            amount_invalid_format: "The request has a missing or invalid amount to charge.",
            amount_too_large: "The request amount to charge is too large.",
            amount_too_small: "The request amount to charge is too small.",
            client_not_authorized_for_user:
                "Point of Sale versions prior to 4.53 require the developer to guide sellers through OAuth before allowing them to take payments with the Point of Sale API. As of Square Point of Sale 4.53, this error type is deprecated. For more information, see OAuth API.",
            could_not_perform:
                "The request couldn't be performed. This is usually because there is an unfinished transaction pending in Square Point of Sale. The seller must open Square Point of Sale and complete the transaction before initiating a new request.",
            currency_code_mismatch:
                "The currency code provided in the request doesn't match the currency associated with the current business.",
            currency_code_missing:
                "The currency code provided in the request is missing or invalid.",
            customer_management_not_supported:
                "This seller account doesn't support customer management and therefore cannot associate transactions with customers.",
            data_invalid:
                "The URL sent to Square Point of Sale has missing or invalid information.",
            invalid_customer_id:
                "The customer ID provided in the request doesn't correspond to a customer signed in to the seller's Customer Directory.",
            invalid_tender_type: "The request included an invalid tender type.",
            no_network_connection:
                "The transaction failed because the device has no network connection.",
            not_logged_in: "A seller isn't currently logged in to Square Point of Sale.",
            payment_canceled: "The seller canceled the payment in Square Point of Sale.",
            unsupported_api_version:
                "The installed version of Square Point of Sale doesn't support the specified version of the Point of Sale API.",
            unsupported_currency_code:
                "The currency code provided in the request isn't currently supported by the Point of Sale API.",
            unsupported_tender_type:
                "The request included a tender type that isn't currently supported by the Point of Sale API.",
            user_id_mismatch:
                "The business location currently signed in to Square Point of Sale doesn't match the location represented by the location_id you provided in your request.",
            user_not_active: "The currently signed-in location hasn't activated card processing.",
            // Android Errors
            CUSTOMER_MANAGEMENT_NOT_SUPPORTED:
                "The Square account used doesn't support customer management.",
            DISABLED: "The Point of Sale API isn't currently available.",
            ILLEGAL_LOCATION_ID:
                "The provided location ID doesn't correspond to the location currently logged in to Square Point of Sale.",
            INVALID_CUSTOMER_ID: "The provided customer ID is invalid.",
            INVALID_REQUEST:
                "The information provided in this transaction request is invalid (such as, a required field is missing or malformed).",
            NO_EMPLOYEE_LOGGED_IN:
                "Employee management is enabled but no employee is logged in to Square Point of Sale.",
            NO_NETWORK:
                "Square Point of Sale was unable to validate the Point of Sale API request because the Android device didn't have an active network connection.",
            NO_RESULT: "Square Point of Sale didn't return a transaction result.",
            TRANSACTION_ALREADY_IN_PROGRESS:
                "Another Square Point of Sale transaction is already in progress.",
            TRANSACTION_CANCELED: "The transaction was canceled in Square Point of Sale.",
            UNAUTHORIZED_CLIENT_ID:
                "The application with the provided client ID isn't authorized to use the Point of Sale API.",
            UNEXPECTED: "An unexpected error occurs.",
            UNSUPPORTED_API_VERSION:
                "The installed version of Square Point of Sale doesn't support this version of the Point of Sale SDK.",
            UNSUPPORTED_WEB_API_VERSION:
                "The Web API used isn't supported in the supplied API version, which must be version 1.3 or later.",
            USER_NOT_ACTIVATED:
                "Square Point of Sale tried to process a credit card transaction, but the associated Square account isn't activated for card processing.",
            USER_NOT_LOGGED_IN: "No user is currently logged in to Square Point of Sale.",
        };

        return squareErrors[code] || "An unknown error occured";
    }
}

registry.category("electronic_payment_interfaces").add("square", PaymentSquare);
