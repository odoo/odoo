import { _t } from "@web/core/l10n/translation";

export class QFPayError extends Error {}

export class QFPay {
    constructor(...args) {
        this.setup(...args);
    }

    setup(env, paymentMethod, errorCallback) {
        this.env = env;
        this.orm = this.env.services.orm;
        this.paymentMethod = paymentMethod;
        this.errorCallback = errorCallback;
    }

    async makeQFPayRequest(endpoint, payload) {
        try {
            const signedPayload = await this.orm.call("pos.payment.method", "qfpay_sign_request", [
                this.paymentMethod.id,
                payload,
            ]);
            const result = await fetch(
                `https://${this.paymentMethod.qfpay_terminal_ip_address}:9001/api/pos/${endpoint}`,
                {
                    method: "POST",
                    headers: {
                        Accept: "application/json",
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify(signedPayload),
                }
            );
            const response = await result.json();

            if (response.respcd !== "6000") {
                // Don't show error message when a request is canceled from the terminal
                if (response.respcd !== "6001") {
                    this.errorCallback(
                        new QFPayError(
                            `Error Code: ${response.respcd}\nError Message: ${
                                response.resperr || response.respmsg || _t("Unknown error occurred")
                            }`
                        )
                    );
                }
                return false;
            }
            return response.data ? JSON.parse(response.data) : true;
        } catch (error) {
            if (error.name == "TypeError" && error.message == "Failed to fetch") {
                this.errorCallback(
                    new QFPayError(
                        _t(
                            "Failed to connect to the QFPay terminal. This might be a certificate issue.\nMake sure you imported the certificates provided by QFPay on this machine."
                        )
                    )
                );
            } else {
                this.errorCallback(error);
            }
        }
    }
}
