import { rpc } from "@web/core/network/rpc";

const REQUEST_TIMEOUT = 10000;

export class RazorpayError extends Error {}

export class Razorpay {
    constructor(...args) {
        this.setup(...args);
    }

    setup(env, razorpayPaymentMethod, access_token, pos_config, errorCallback) {
        this.env = env;
        this.access_token = access_token;
        this.razorpayPaymentMethod = razorpayPaymentMethod;
        this.pos_config = pos_config;
        this.errorCallback = errorCallback;
        this.savedOrder = false;
        this.pollTimeout = null;
        this.inactivityTimeout = null;
        this.queued = false;
        this.payment_stopped = false;
    }

    handleRazorpayResponse(response) {
        if (response?.error) {
            this.payment_stopped
                ? this.errorCallback(new RazorpayError("Transaction canceled due to inactivity"))
                : this.errorCallback(new RazorpayError(response.error));
            this.removePaymentHandler(["p2pRequestId"]);
            return false;
        }
        localStorage.setItem("p2pRequestId", response?.p2pRequestId);
        return true;
    }

    async cancelPayment(order) {
        const data = { p2pRequestId: localStorage.getItem("p2pRequestId") };
        try {
            const cancel_response = await rpc("/pos-self-order/razorpay-cancel-transaction/", {
                access_token: this.access_token,
                order_id: order.id,
                payment_data: data,
                payment_method_id: this.razorpayPaymentMethod.id,
            });
            if (cancel_response) {
                if (cancel_response?.errorMessage) {
                    this.errorCallback(cancel_response.errorMessage, "warning");
                    return true;
                }
                return this.handleRazorpayResponse(cancel_response);
            }
        } catch (error) {
            this.errorCallback(error);
            return false;
        }
    }

    async startPayment(order) {
        const call_razorpay = await this.processPayment(order);
        if (call_razorpay) {
            await this.paymentPolling(this.savedOrder);
        }
    }

    async processPayment(order) {
        try {
            const initial_response = await rpc(`/kiosk/payment/${this.pos_config.id}/kiosk`, {
                order: order.serializeForORM(),
                access_token: this.access_token,
                payment_method_id: this.razorpayPaymentMethod.id,
            });
            if (initial_response) {
                this.savedOrder = initial_response.order[0];
                return this.handleRazorpayResponse(initial_response.payment_status);
            }
        } catch (error) {
            this.errorCallback(error);
            return false;
        }
    }

    /**
     * Polling
     * This method calls and handles the razorpay payment status
     * calls every 10 sec until payment status not found.
     */
    async paymentPolling(order) {
        const data = { p2pRequestId: localStorage.getItem("p2pRequestId") };
        this.stopInactivePayment().then(() => (this.payment_stopped = true));
        const fetchPaymentStatus = async () => {
            try {
                // Within 90 seconds, inactivity will result in transaction cancellation and payment termination.
                if (this.payment_stopped) {
                    await this.cancelPayment(order);
                    return false;
                }

                const polling_response = await rpc(
                    "/pos-self-order/razorpay-fetch-payment-status/",
                    {
                        access_token: this.access_token,
                        order_id: order.id,
                        payment_data: data,
                        payment_method_id: this.razorpayPaymentMethod.id,
                    }
                );
                if (polling_response?.error) {
                    this.handleRazorpayResponse(polling_response);
                    return false;
                }

                const result_code = polling_response?.status;

                if (result_code === "QUEUED" && this.queued === false) {
                    await this.cancelPayment(order);
                    await this.startPayment(order);
                }
                if (result_code === "AUTHORIZED") {
                    this.removePaymentHandler(["p2pRequestId"]);
                    return true;
                } else {
                    // clearing previous timeout before setting a new one
                    clearTimeout(this.pollTimeout);
                    this.pollTimeout = setTimeout(fetchPaymentStatus, REQUEST_TIMEOUT);
                }
            } catch (error) {
                this.errorCallback(error);
            }
        };
        await fetchPaymentStatus();
    }

    stopInactivePayment() {
        return new Promise((resolve) => (this.inactivityTimeout = setTimeout(resolve, 90000)));
    }

    removePaymentHandler(payment_data) {
        payment_data.forEach((data) => {
            localStorage.removeItem(data);
        });
        clearTimeout(this.pollTimeout);
        clearTimeout(this.inactivityTimeout);
        this.queued = this.payment_stopped = false;
    }
}
