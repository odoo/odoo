import { Logger } from "@bus/workers/bus_worker_utils";
import { reactive } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

const CASHDRO_URL = "/Cashdro3WS/index3.php";

/**
 * @typedef {{
 *   operation: {
 *     operation: {
 *       operationid: string;
 *       state: "I" | "Q" | "E" | "F";
 *       total: string
 *       totalin: string
 *       totalout: string
 *     }
 *     messages: string[];
 *     withError: "false" | "true";
 *   }
 * }} CashdroOperation
 */

const OPERATION_STATE = {
    INIT: "I",
    QUEUED: "Q",
    EXECUTING: "E",
    FINISHED: "F",
};

const SUCCESS_RESULT_CODE = 1;

const PAYMENT_TRANSACTION_TYPE = 4;
const REFUND_TRANSACTION_TYPE = 3;

export class CashdroService {
    constructor() {
        this.setup(...arguments);
    }

    setup() {
        this.logger = new Logger("pos_cashdro");
        this._resetState();
    }

    /**
     * @param {string} ip
     * @param {string} username
     * @param {string} password
     * @param {boolean} [forceHttp]
     */
    connect(ip, username, password, forceHttp = false) {
        this._resetState();
        this.ip = ip;
        this.username = username;
        this.password = password;
        this.forceHttp = forceHttp;
    }

    /**
     * @param {number} amountInCents
     * @returns {Promise<string>}
     */
    async sendPaymentRequest(amountInCents) {
        this.state.amountInserted = 0;
        const operationType =
            amountInCents < 0 ? REFUND_TRANSACTION_TYPE : PAYMENT_TRANSACTION_TYPE;
        const response = await this._sendRequest("startOperation", {
            type: operationType,
            parameters: JSON.stringify({ amount: Math.abs(amountInCents).toString() }),
        });
        await this._sendRequest("acknowledgeOperationId", {
            operationId: response.operation.operationId,
        });
        return response.operation.operationId;
    }

    /** @returns {Promise<string | null>} */
    async getCurrentlyExecutingOperation() {
        const { operation } = await this._sendRequest("askOperationExecuting");
        if (operation?.OperationId && operation.OperationId > 0) {
            return operation.OperationId;
        }
        return null;
    }

    /** @param {string} operationId */
    async cancelPayment(operationId) {
        return await this._sendRequest("finishOperation", {
            operationId,
            type: 3,
        });
    }

    _resetState() {
        this.ip = null;
        this.username = null;
        this.password = null;
        this.forceHttp = false;
        this.state = reactive({ amountInserted: 0 });
    }

    /**
     * @param {string} operationId
     * @returns {Promise<CashdroOperation['operation']>}
     */
    async waitForPaymentCompletion(operationId) {
        /** @type {CashdroOperation} */
        const { operation } = await this._sendRequest("askOperation", { operationId });

        this.state.amountInserted = parseInt(operation.operation.totalin);
        const operationState = operation.operation.state;
        if (operationState === OPERATION_STATE.FINISHED) {
            return operation;
        }

        await new Promise((resolve) => setTimeout(resolve, 3000));
        return this.waitForPaymentCompletion(operationId);
    }

    /**
     * @param {string} operation
     * @param {Record<string, string>} [params]
     * @returns {Promise<Record<string, unknown>>}
     */
    async _sendRequest(operation, params = {}) {
        const protocol = this.forceHttp ? "http:" : window.location.protocol;
        const queryParams = new URLSearchParams({
            operation,
            name: this.username,
            password: this.password,
            ...params,
        });
        const url = `${protocol}//${this.ip}${CASHDRO_URL}?${queryParams}`;
        this._log("REQUEST", url);

        try {
            const response = await fetch(url, {
                targetAddressSpace: this.forceHttp ? "local" : undefined,
            });

            if (!response.ok) {
                this._log("HTTP ERROR", `${url}: ${response.status}`);
                throw new Error(response.statusText);
            }
            const cashdroResult = await response.json();
            this._log("RESPONSE", cashdroResult);
            if (cashdroResult.code !== SUCCESS_RESULT_CODE) {
                throw new Error(cashdroResult.response.errorMessage);
            }

            return cashdroResult.response;
        } catch (error) {
            if (error instanceof TypeError) {
                this._log("NETWORK ERROR", error.message);
                throw new Error(
                    _t(
                        "Could not reach cash machine on the network, please check your IP and/or LNA settings."
                    )
                );
            }
            throw error;
        }
    }

    /**
     * @param {string} message
     * @param {any} payload
     */
    _log(message, payload) {
        this.logger.log(
            `${luxon.DateTime.now().toFormat("yyyy-LL-dd HH:mm:ss")} ${message}: ${JSON.stringify(
                payload
            )}`
        );
    }
}
