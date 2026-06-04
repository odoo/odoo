import { proxy } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class CashmaticError extends Error {
    constructor(message, status) {
        super(message);
        this.status = status;
    }
}

const HTTPS_PORT = 50301;
const HTTP_PORT = 80;
export const POST_REQUESTS = {
    login: "/api/user/Login",
    renewToken: "/api/user/RenewToken",
    startPayment: "/api/transaction/StartPayment",
    cancelPayment: "/api/transaction/CancelPayment",
    activeTransaction: "/api/device/ActiveTransaction",
    lastTransaction: "/api/device/LastTransaction",
    startWithdrawal: "/api/transaction/StartWithdrawal",
};

export class CashmaticService {
    connect(ip, username, password, forceHttp = false) {
        this.ip = ip;
        this.username = username;
        this.password = password;
        this.forceHttp = forceHttp;
        this.token = null;
        this.state = proxy({ amountInserted: 0, amountDispensed: 0 });
    }

    async _sendRequest(operation, params) {
        const protocol = this.forceHttp ? "http:" : window.location.protocol;
        const port = this.forceHttp ? HTTP_PORT : HTTPS_PORT;
        const url = `${protocol}//${this.ip}:${port}${operation}`;
        let response;
        try {
            response = await fetch(url, {
                method: "POST",
                signal: AbortSignal.timeout(5000),
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${this.token}`,
                },
                body: JSON.stringify(params),
                targetAddressSpace: this.forceHttp ? "local" : undefined,
            });
        } catch (e) {
            if (e.name === "TimeoutError" || e.name === "AbortError") {
                throw new Error(_t("Cashmatic device unreachable"));
            }
            throw e;
        }

        if (!response.ok) {
            throw new CashmaticError(response.statusText, response.status);
        }

        const cashmaticResult = await response.json();
        if (cashmaticResult.code !== 0) {
            throw new Error(cashmaticResult.message);
        }
        return cashmaticResult.data;
    }

    async cancelCurrentPayment() {
        await this.renewOrLogin();
        await this._sendRequest(POST_REQUESTS.cancelPayment, {});
        return await this._cashmaticStatus();
    }
    async sendPaymentRequest(amount, reference) {
        this.state.amountInserted = 0;
        this.state.amountDispensed = 0;
        await this.renewOrLogin();
        await this._sendRequest(POST_REQUESTS.startPayment, {
            amount,
            reference,
        });
        return await this._cashmaticStatus();
    }

    async sendWithdrawalRequest(amount, reference) {
        this.state.amountInserted = 0;
        this.state.amountDispensed = 0;
        await this.renewOrLogin();
        await this._sendRequest(POST_REQUESTS.startWithdrawal, {
            amount,
            reference,
        });
        return await this._cashmaticStatus();
    }

    async _cashmaticStatus() {
        try {
            const response = await this._sendRequest(POST_REQUESTS.activeTransaction, {});
            if (response.operation !== "idle") {
                await new Promise((resolve) => setTimeout(resolve, 200));
                this.state.amountInserted = response.inserted;
                this.state.amountDispensed = response.dispensed;
                return await this._cashmaticStatus();
            }
            const lastResponse = await this._sendRequest(POST_REQUESTS.lastTransaction, {});
            return lastResponse.notDispensed;
        } catch (e) {
            if (e instanceof CashmaticError && (e.status === 401 || e.status === 403)) {
                await this.renewOrLogin();
                return await this._cashmaticStatus();
            }
            throw e;
        }
    }
    async renewOrLogin() {
        try {
            const response = await this._sendRequest(POST_REQUESTS.renewToken, {});
            if (!response?.token) {
                throw new Error("No token");
            }
            this.token = response.token;
        } catch {
            const response = await this._sendRequest(POST_REQUESTS.login, {
                username: this.username,
                password: this.password,
            });
            if (!response?.token) {
                throw new Error("No token");
            }
            this.token = response.token;
        }
    }
}
