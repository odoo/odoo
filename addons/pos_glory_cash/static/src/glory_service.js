import {
    serializeGloryXml,
    parseGloryXml,
    makeGloryHeader,
    parseGloryResult,
    parseVerificationInfo,
} from "@pos_glory_cash/utils/glory_xml";
import {
    GLORY_STATUS,
    GLORY_CURRENCY_STATUS,
    WEBSOCKET_REQUESTS,
    XML_REQUESTS,
} from "@pos_glory_cash/utils/constants";
import { SocketIoService } from "@pos_glory_cash/utils/socket_io";
import { reactive } from "@odoo/owl";
import { sortBy } from "@web/core/utils/arrays";
import { browser } from "@web/core/browser/browser";
import { Logger } from "@bus/workers/bus_worker_utils";
import { uuid } from "@web/core/utils/strings";

const { DateTime } = luxon;

const WEBSOCKET_PORT = browser.location.protocol === "https:" ? 3001 : 3000;
const WEBSOCKET_PROTOCOL = browser.location.protocol === "https:" ? "wss:" : "ws:";
const WEBSOCKET_URL = "/socket.io/?transport=websocket&EIO=3";

const convertObjectValuesToInt = (object) =>
    Object.fromEntries(Object.entries(object).map(([key, value]) => [key, parseInt(value)]));

export class GloryService {
    /**
     * @param {(status: string) => void} onStatusChange
     */
    constructor(onStatusChange) {
        this.setup(...arguments);
    }

    /**
     * @param {(status: string) => void} onStatusChange
     */
    setup(onStatusChange) {
        this.logger = new Logger("pos_glory_cash");
        this.eventHandlers = {
            StatusChangeEvent: this._statusChangeHandler.bind(this),
            InventoryResponse: this._inventoryChangeHandler.bind(this),
            SpecialDeviceError: this._deviceErrorHandler.bind(this),
        };
        this.onStatusChange = onStatusChange;
        this.socketIo = new SocketIoService({
            onConnect: () => this._onConnect(),
            onClose: () => {
                this.status = "DISCONNECTED";
            },
            onEvent: ([responseType, data]) => {
                if (this.resolvers[responseType]) {
                    this.resolvers[responseType](data);
                }
            },
            onBinaryEvent: (data) =>
                parseGloryXml(data).then((response) => {
                    this._logXml("RECV", response);
                    const message = response.firstChild;
                    if (this.resolvers[message.tagName]) {
                        this.resolvers[message.tagName](message);
                    } else if (this.eventHandlers[message.tagName]) {
                        this.eventHandlers[message.tagName](message);
                    }
                }),
        });
        this._resetState();
    }

    /**
     * @param {string} ip
     * @param {string} [username]
     * @param {string} [password]
     */
    connect(ip, username, password) {
        this._resetState();
        this.username = username;
        this.password = password;
        const websocketEndpoint = `${WEBSOCKET_PROTOCOL}//${ip}:${WEBSOCKET_PORT}${WEBSOCKET_URL}`;
        this.socketIo.connect(websocketEndpoint);
    }

    async reset() {
        if (this.settings.OccupyEnable && !this.occupied) {
            await this._occupy();
        }

        await this._sendXmlRequest(XML_REQUESTS.reset);

        if (this.occupied) {
            await this._release();
        }
    }

    /**
     * @param {number} amountInCents
     * @returns {Promise<{ status: string, cashGiven?: number, cashReturned?: number, transactionId?: string }>}
     */
    async sendPaymentRequest(amountInCents) {
        if (
            [
                "DISCONNECTED",
                "BAD_CREDENTIALS",
                "ERROR",
                "WAITING_ERROR_RECOVERY",
                "WAITING_REPLENISHMENT",
                "COLLECTING",
            ].includes(this.status)
        ) {
            return {
                status: this.status,
            };
        }

        if (this.settings.OccupyEnable) {
            await this._occupy();
        }

        this.state.amountInserted = 0;
        this.paymentInProgress = true;
        this._newSequenceNumber();

        const { xmlResponse } = await this._sendXmlRequest(XML_REQUESTS.startPayment, [
            {
                name: "Amount",
                children: [amountInCents.toString()],
            },
            {
                // Option Type 1 = Enable cancellation when there is insufficient change
                name: "Option",
                attributes: { type: "1" },
            },
        ]);

        const result = await this._handlePaymentResponse(xmlResponse);

        if (this.occupied) {
            await this._release();
        }
        this.paymentInProgress = false;

        return result;
    }

    async initiatePaymentCancel() {
        if (this.status === "DISCONNECTED") {
            return this.status;
        }

        if (this.settings.OccupyEnable && !this.occupied) {
            const occupyResult = await this._occupy();
            if (occupyResult !== "SUCCESS") {
                return occupyResult;
            }
        }

        const { statusCode } = await this._sendXmlRequest(XML_REQUESTS.cancelPayment);

        if (this.occupied && !this.paymentInProgress) {
            await this._release();
        }

        return statusCode;
    }

    get status() {
        return this.state.status;
    }
    set status(newStatus) {
        if (newStatus === this.state.status) {
            return;
        }
        this.state.status = newStatus;
        this.onStatusChange(newStatus);
    }

    _resetState() {
        /**
         * @type {import("models").GlorySettings}
         */
        this.settings = null;
        /**
         * @type {import("models").GloryUser}
         */
        this.gloryUser = null;
        this.username = null;
        this.password = null;
        this.sequenceNumber = 0;
        this.sessionId = null;
        this.occupied = false;
        this.paymentInProgress = false;

        /** @type {import("models".GloryState)} */
        this.state = reactive({
            status: "DISCONNECTED",
            inventory: [],
            amountInserted: 0,
            lastDeviceError: null,
        });

        this.resolvers = {};
    }

    async _onConnect() {
        await this._login();

        if (!this.settings) {
            const settings = await this._sendWebsocketRequest(WEBSOCKET_REQUESTS.getSettings);
            this.settings = convertObjectValuesToInt(settings.FunctionSetting);
        }

        if (this.settings.SessionEnable) {
            await this._refreshSession();
        }

        await this._setDateAndTime();
        await this._checkStatusAndVerifyIfNeeded();

        const { xmlResponse } = await this._sendXmlRequest(XML_REQUESTS.getInventory, [
            // Option Type 2 = 'Payable' inventory, see p76 of the IF Specification document
            { name: "Option", attributes: { type: "2" } },
        ]);
        this._inventoryChangeHandler(xmlResponse);
    }

    async _login() {
        if (this.username) {
            const response = await this._sendWebsocketRequest(
                WEBSOCKET_REQUESTS.login,
                this.username,
                this.password
            );
            if (response.ret === 0) {
                this.gloryUser = response;
            }
        }

        // If access control is enabled and we don't have a valid user/pass, we receive this 'credential ng' message
        this._waitForResponseWithType("credential ng").then(() => {
            this.status = "BAD_CREDENTIALS";
        });
        await this._sendWebsocketRequest(
            WEBSOCKET_REQUESTS.checkCredentials,
            this.gloryUser?.session_id
        );
    }

    async _refreshSession() {
        const data = await this._sendWebsocketRequest(WEBSOCKET_REQUESTS.openSession);
        this.sessionId = data.SessionID;
    }

    async _setDateAndTime() {
        const now = DateTime.now();
        await this._sendXmlRequest(XML_REQUESTS.setDateAndTime, [
            {
                name: "Date",
                attributes: {
                    year: now.year.toString(),
                    month: now.month.toString(),
                    day: now.day.toString(),
                },
            },
            {
                name: "Time",
                attributes: {
                    hour: now.hour.toString(),
                    minute: now.minute.toString(),
                    second: now.second.toString(),
                },
            },
        ]);
    }

    async _checkStatusAndVerifyIfNeeded() {
        const firstConnection = this.state.inventory.length === 0;
        const { xmlResponse } = await this._sendXmlRequest(XML_REQUESTS.getStatus, [
            { name: "RequireVerification", attributes: { type: "1" } },
        ]);
        this._statusChangeHandler(xmlResponse);

        const requireVerifyType = parseVerificationInfo(xmlResponse);
        if (!firstConnection || !requireVerifyType) {
            return;
        }

        const { statusCode } = await this._sendXmlRequest(XML_REQUESTS.collect, [
            { name: "RequireVerification", attributes: { type: requireVerifyType.toString() } },
        ]);

        return statusCode;
    }

    /**
     * @param {Element} statusResponse
     */
    _statusChangeHandler(statusResponse) {
        const statusCodeElement =
            statusResponse.getElementsByTagName("Code")[0] ??
            statusResponse.getElementsByTagName("Status")[0];

        this.status = GLORY_STATUS[statusCodeElement.textContent];

        if (!["ERROR", "WAITING_ERROR_RECOVERY"].includes(this.status)) {
            this.state.lastDeviceError = null;
        }

        if (this.status === "COUNTING") {
            const amount = statusResponse.getElementsByTagName("Amount")[0].textContent;
            this.state.amountInserted = parseInt(amount);
        }
    }

    /**
     * @param {Element} inventoryResponse
     */
    _inventoryChangeHandler(inventoryResponse) {
        const cashElements = Array.from(inventoryResponse.getElementsByTagName("Cash"));
        const dispensableCash = cashElements.find(
            (cashElement) => cashElement.getAttribute("type") === "4"
        );
        if (!dispensableCash) {
            return;
        }

        const denominations = this._parseGloryCashElement(dispensableCash);
        this.state.inventory = sortBy(denominations, "value");
    }

    /**
     * @param {Element} deviceErrorResponse
     */
    _deviceErrorHandler(deviceErrorResponse) {
        const errorMessageElement = deviceErrorResponse.getElementsByTagName("ErrorMessage")[0];
        this.state.lastDeviceError = errorMessageElement.textContent;
    }

    /**
     * @param {Element} cashElement
     */
    _parseGloryCashElement(cashElement) {
        const denominationElements = Array.from(cashElement.getElementsByTagName("Denomination"));
        return denominationElements.map((denomination) => ({
            value: parseInt(denomination.getAttribute("fv")),
            amount: parseInt(denomination.getElementsByTagName("Piece")[0].textContent),
            status: GLORY_CURRENCY_STATUS[
                denomination.getElementsByTagName("Status")[0].textContent
            ],
        }));
    }

    /**
     * @param {Element} cashElement
     * @returns {number}
     */
    _getTotalFromGloryCashElement(cashElement) {
        const denominations = this._parseGloryCashElement(cashElement);
        return denominations.reduce((total, next) => total + next.amount * next.value, 0);
    }

    _newSequenceNumber() {
        this.sequenceNumber = uuid().replace("-", "").slice(0, 11);
    }

    /**
     * @param {Element} paymentResponse
     * @returns {Promise<{ status: string, cashGiven?: number, cashReturned?: number, transactionId?: string }>}
     */
    async _handlePaymentResponse(paymentResponse) {
        const baseResponse = {
            status: parseGloryResult(paymentResponse),
        };
        if (["SUCCESS", "CHANGE_SHORTAGE"].includes(baseResponse.status)) {
            return {
                ...baseResponse,
                ...this._getTransactionInfo(paymentResponse),
            };
        }
        return baseResponse;
    }

    /**
     * @param {Element} paymentResponse
     */
    _getTransactionInfo(paymentResponse) {
        const cashElements = Array.from(paymentResponse.getElementsByTagName("Cash"));
        const cashGivenElement = cashElements.find(
            (cashElement) => cashElement.getAttribute("type") === "1"
        );
        const cashReturnedElement = cashElements.find(
            (cashElement) => cashElement.getAttribute("type") === "2"
        );
        const cashGiven = this._getTotalFromGloryCashElement(cashGivenElement);
        const cashReturned = this._getTotalFromGloryCashElement(cashReturnedElement);
        const transactionId = paymentResponse.getElementsByTagName("TransactionId")[0].textContent;

        return {
            cashGiven,
            cashReturned,
            transactionId,
        };
    }

    async _occupy() {
        const { statusCode } = await this._sendXmlRequest(XML_REQUESTS.occupy);
        if (statusCode === "SUCCESS") {
            this.occupied = true;
        }
        return statusCode;
    }

    async _release() {
        await this._sendXmlRequest(XML_REQUESTS.release);
        this.occupied = false;
    }

    /**
     * @param {import("models").GloryRequestInfo} request
     * @param {any[]} params
     */
    _sendWebsocketRequest(request, ...params) {
        const resultPromise = this._waitForResponseWithType(request.responseName);
        this.socketIo.sendMessage([request.requestName, ...params]);
        return resultPromise;
    }

    /**
     * @param {import("models").GloryRequestInfo} request
     * @param {import("models").GloryXmlElement[]?} children
     * @returns {Promise<{ statusCode: string, xmlResponse: Element }>}
     */
    async _sendXmlRequest(request, children, secondAttempt = false) {
        const xmlElement = {
            name: request.requestName,
            children: [
                ...makeGloryHeader(this.sequenceNumber, this.sessionId),
                ...(children ?? []),
            ],
        };
        const xmlString = serializeGloryXml(xmlElement);
        this._logXml("SEND", xmlString);
        this.socketIo.sendMessage(["xml send", xmlString]);

        const xmlResponse = await this._waitForResponseWithType(request.responseName);
        const statusCode = parseGloryResult(xmlResponse);

        if (
            !secondAttempt &&
            (statusCode === "SESSION_TIMEOUT" || statusCode === "INVALID_SESSION")
        ) {
            await this._refreshSession();
            return this._sendXmlRequest(request, children, true);
        }

        return { statusCode, xmlResponse };
    }

    /**
     * @param {string} type
     * @returns {Promise<Element>}
     */
    async _waitForResponseWithType(type) {
        const responsePromise = new Promise((resolve) => {
            this.resolvers[type] = resolve;
        });
        const result = await responsePromise;
        this.resolvers[type] = null;
        return result;
    }

    _logXml(message, xml) {
        if (typeof xml === "string") {
            xml = xml.replace("\0", "");
        } else {
            xml = new XMLSerializer().serializeToString(xml);
        }

        this.logger.log(
            `${luxon.DateTime.now().toFormat("yyyy-LL-dd HH:mm:ss")} ${message}: ${xml}`
        );
    }
}
