import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";

const REQUEST_TIMEOUT = 5000;
const INACTIVITY_TIMEOUT = 90000;

export class PineLabsError extends Error {}

export class PineLabs {
    constructor(...args) {
        this.setup(...args);
    }

    setup(pos_data, pineLabsPaymentMethod, access_token, pos_config, errorCallback) {
        this.pos_data = pos_data;
        this.pineLabsPaymentMethod = pineLabsPaymentMethod;
        this.access_token = access_token;
        this.pos_config = pos_config;
        this.errorCallback = errorCallback;
        this.savedOrder = false;
        this.pollTimeout = null;
        this.inactivityTimeout = null;
        this.paymentStopped = false;
    }

    _callPineLabs(data, action, model = "pos.payment.method", id = this.pineLabsPaymentMethod.id) {
        return this.pos_data.call(model, action, [[id], data]);
    }

    async startPayment(order) {
        const paymentRequestResponse = await this.processPayment(order);
        if (paymentRequestResponse) {
            await this.paymentPolling(this.savedOrder);
        }
        this.removePaymentHandler(["plutusTransactionReferenceID", "paymentRefNo"]);
    }

    async processPayment(order) {
        try {
            const initialResponse = await rpc(`/kiosk/payment/${this.pos_config.id}/kiosk`, {
                order: order.serializeForORM(),
                access_token: this.access_token,
                payment_method_id: this.pineLabsPaymentMethod.id,
            });
            if (initialResponse) {
                this.savedOrder = initialResponse.order[0];
                return this.handlePineLabsResponse(initialResponse.payment_status);
            }
        } catch (error) {
            this.errorCallback(error);
            return false;
        }
    }

    async cancelPayment(order) {
        try {
            // We need to provide the amount in paisa since Pine Labs processes amounts in paisa.
            // The conversion rate between INR and paisa is set as 1 INR = 100 paisa.
            const data = {
                plutusTransactionReferenceID: localStorage.getItem("plutusTransactionReferenceID"),
                amount: order.amount_total * 100,
            };
            const cancelResponse = await this._callPineLabs(
                data,
                "pine_labs_cancel_payment_request"
            );

            if (cancelResponse) {
                // Successfully cancelled the transaction
                if (cancelResponse.notification) {
                    this.errorCallback(new PineLabsError(cancelResponse.notification, "warning"));
                    return true;
                }
                return this.handlePineLabsResponse(cancelResponse);
            }
        } catch (error) {
            this.errorCallback(error);
            return false;
        }
    }

    /**
     * Polls Pine Labs payment status at regular intervals (5 seconds)
     * until a payment is approved, a timeout occurs, or the transaction is stopped.
     *
     * This ensures that we handle both successful and failed payments gracefully
     * by continuously checking the status until a final state is reached.
     */
    async paymentPolling(order) {
        this.stopInactivePayment().then(() => (this.paymentStopped = true));
        const fetchPaymentStatus = async (resolve, reject) => {
            try {
                clearTimeout(this.pollTimeout);
                // This transaction will automatically cancel if inactive for more than 90 seconds.
                if (this.paymentStopped) {
                    await this.cancelPayment(order);
                    return resolve(false);
                }

                const statusResponse = await this._callPineLabs(
                    {
                        plutusTransactionReferenceID: localStorage.getItem(
                            "plutusTransactionReferenceID"
                        ),
                    },
                    "pine_labs_fetch_payment_status"
                );
                if (!statusResponse) {
                    this.errorCallback(
                        new PineLabsError(_t("Failed to fetch the payment status."))
                    );
                    return resolve(false);
                }
                if (statusResponse.error) {
                    this.handlePineLabsResponse(statusResponse);
                    return resolve(false);
                }

                if (statusResponse.status === "TXN APPROVED") {
                    return resolve(await this._paymentStatusRequestHandler(statusResponse, order));
                }

                this.pollTimeout = setTimeout(fetchPaymentStatus, REQUEST_TIMEOUT, resolve, reject);
            } catch (error) {
                this.errorCallback(error);
                return resolve(false);
            }
        };
        return new Promise(fetchPaymentStatus);
    }

    async _paymentStatusRequestHandler(response, order) {
        try {
            const data = response.data;
            data["payment_ref_no"] = localStorage.getItem("paymentRefNo");
            data["pine_labs_plutus_transaction_ref"] = localStorage.getItem(
                "plutusTransactionReferenceID"
            );
            // Pass the system's local timezone to the backend to accurately process and convert local datetime values in Python.
            data["time_zone"] = luxon.DateTime.local().zone.name;
            await this.pos_data.call("pos.payment.method", "handle_pine_labs_payment_response", [
                [this.pineLabsPaymentMethod.id],
                order.id,
                data,
            ]);
            return true;
        } catch (error) {
            this.errorCallback(error);
            return false;
        }
    }

    handlePineLabsResponse(response) {
        if (response.error) {
            this.errorCallback(new PineLabsError(response.error));
            return false;
        }
        response.plutusTransactionReferenceID &&
            localStorage.setItem(
                "plutusTransactionReferenceID",
                response.plutusTransactionReferenceID
            );
        response.payment_ref_no && localStorage.setItem("paymentRefNo", response.payment_ref_no);
        return true;
    }

    stopInactivePayment() {
        return new Promise(
            (resolve) => (this.inactivityTimeout = setTimeout(resolve, INACTIVITY_TIMEOUT))
        );
    }

    removePaymentHandler(payment_data) {
        payment_data.forEach((data) => {
            localStorage.removeItem(data);
        });
        clearTimeout(this.pollTimeout);
        clearTimeout(this.inactivityTimeout);
        this.paymentStopped = false;
    }
}
