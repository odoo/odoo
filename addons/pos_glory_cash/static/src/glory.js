import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { uuidv4 } from "@point_of_sale/utils";
import { CancelDialog } from "@pos_glory_cash/app/components/cancel_dialog";
import {
    serializeGloryXml,
    parseGloryXml,
    makeGloryHeader,
    parseGloryResult,
    parseVerificationInfo,
} from "@pos_glory_cash/utils/glory_xml";
import {
    GLORY_STATUS,
    GLORY_STATUS_STRING,
    GLORY_CURRENCY_STATUS,
    WEBSOCKET_REQUESTS,
    XML_REQUESTS,
} from "@pos_glory_cash/utils/constants";
import { SocketIoService } from "@pos_glory_cash/utils/socket_io";
import { reactive } from "@odoo/owl";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { sortBy } from "@web/core/utils/arrays";
import { browser } from "@web/core/browser/browser";
import { ask } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { Logger } from "@bus/workers/bus_worker_utils";

const { DateTime } = luxon;

const WEBSOCKET_PORT = browser.location.protocol === "https:" ? 3001 : 3000;
const WEBSOCKET_PROTOCOL = browser.location.protocol === "https:" ? "wss:" : "ws:";
const WEBSOCKET_URL = "/socket.io/?transport=websocket&EIO=3";

export class GloryService extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        this.dialog = this.env.services.dialog;
        this.logger = new Logger("pos_glory_cash");

        /**
         * @type {import("models").GlorySettings}
         */
        this.settings = null;
        /**
         * @type {import("models").GloryUser}
         */
        this.gloryUser = null;
        this.sequenceNumber = 0;
        this.sessionId = null;
        this.occupied = false;

        this.cancellationResolver = null;
        this.resolvers = {};

        this.state = reactive({
            status: "DISCONNECTED",
            inventory: [],
            amountInserted: 0,
        });

        this.eventHandlers = {
            StatusChangeEvent: this.statusChangeHandler.bind(this),
            InventoryResponse: this.inventoryChangeHandler.bind(this),
        };

        this.setupWebsocket();
    }

    setupWebsocket() {
        const websocketEndpoint = `${WEBSOCKET_PROTOCOL}//${this.payment_method_id.glory_websocket_address}:${WEBSOCKET_PORT}${WEBSOCKET_URL}`;

        this.socketIo = new SocketIoService(websocketEndpoint, {
            onConnect: () => this.onConnect(),
            onClose: () => {
                if (this.state.status !== "DISCONNECTED") {
                    this.state.status = "DISCONNECTED";
                    // When the tab is in the background, we get false-positive disconnections due to the ping running too
                    // slowly (Chrome slows down timers for inactive tabs). Therefore we only show the disconnection message
                    // if the tab is focused.
                    if (!document.hidden) {
                        this.showError(
                            _t(
                                "Failed to connect to Glory cash machine, please ensure it is switched on and connected to the network."
                            )
                        );
                    }
                }
            },
            onEvent: ([responseType, data]) => {
                if (this.resolvers[responseType]) {
                    this.resolvers[responseType](data);
                }
            },
            onBinaryEvent: (data) =>
                parseGloryXml(data).then((response) => {
                    this.logXml("RECV", response);
                    const message = response.firstChild;
                    if (this.resolvers[message.tagName]) {
                        this.resolvers[message.tagName](message);
                    } else if (this.eventHandlers[message.tagName]) {
                        this.eventHandlers[message.tagName](message);
                    }
                }),
        });

        setTimeout(() => {
            if (this.state.status === "DISCONNECTED") {
                this.showError(
                    _t(
                        "Failed to connect to Glory cash machine, please ensure it is switched on and connected to the network."
                    )
                );
            }
        }, 5000);
    }

    async login() {
        if (this.payment_method_id.glory_username) {
            const response = await this.sendWebsocketRequest(
                WEBSOCKET_REQUESTS.login,
                this.payment_method_id.glory_username,
                this.payment_method_id.glory_password
            );
            if (response.ret === 0) {
                this.gloryUser = response;
            }
        }

        // If access control is enabled and we don't have a valid user/pass, we receive this 'credential ng' message
        this.waitForResponseWithType("credential ng").then(() => {
            this.state.status = "BAD_CREDENTIALS";
            this.showError(
                _t(
                    "Failed to login to Glory cash machine, please check the configured username and password."
                )
            );
        });
        await this.sendWebsocketRequest(
            WEBSOCKET_REQUESTS.checkCredentials,
            this.gloryUser?.session_id
        );
    }

    async checkStatusAndVerifyIfNeeded() {
        const firstConnection = this.state.inventory.length === 0;
        const { xmlResponse } = await this.sendXmlRequest(XML_REQUESTS.getStatus, [
            { name: "RequireVerification", attributes: { type: "1" } },
        ]);
        this.statusChangeHandler(xmlResponse, true);

        const requireVerifyType = parseVerificationInfo(xmlResponse);
        if (!firstConnection || !requireVerifyType) {
            return;
        }

        this.showError(
            _t(
                "The cash machine requires verification of its contents, a collection process will now start. Please refer to the cash machine display."
            )
        );

        const { statusCode } = await this.sendXmlRequest(XML_REQUESTS.collect, [
            { name: "RequireVerification", attributes: { type: requireVerifyType.toString() } },
        ]);

        if (statusCode === "EXCLUSIVE_ERROR") {
            this.showError(
                _t(
                    "The cash machine contents could not be verified as it is busy with another operation."
                )
            );
        }
    }

    async reset(skipDialog = false) {
        if (!skipDialog) {
            const userConfirmed = await ask(this.dialog, {
                title: _t("Reset cash machine"),
                body: _t("Are you sure you want to reset the cash machine?"),
                confirmLabel: _t("Reset"),
                cancelLabel: _t("Discard"),
            });
            if (!userConfirmed) {
                return;
            }
        }

        if (this.settings.OccupyEnable && !this.occupied) {
            await this.occupy();
        }

        await this.sendXmlRequest(XML_REQUESTS.reset);

        if (this.occupied) {
            await this.release();
        }
    }

    logXml(message, xml) {
        if (typeof xml === "string") {
            xml = xml.replace("\0", "");
        } else {
            xml = new XMLSerializer().serializeToString(xml);
        }

        this.logger.log(
            `${luxon.DateTime.now().toFormat("yyyy-LL-dd HH:mm:ss")} ${message}: ${xml}`
        );
    }

    async downloadLogs() {
        const logs = await this.logger.getLogs();
        const blob = new Blob([logs.join("\n")], {
            type: "text/plain",
        });
        const url = URL.createObjectURL(blob);
        const aElement = document.createElement("a");
        aElement.href = url;
        aElement.download = `glory_logs_${luxon.DateTime.now().toFormat(
            "yyyy-LL-dd-HH-mm-ss"
        )}.txt`;
        aElement.click();
        URL.revokeObjectURL(url);
    }

    async onConnect() {
        await this.login();

        const settings = await this.sendWebsocketRequest(WEBSOCKET_REQUESTS.getSettings);
        this.settings = settings.FunctionSetting;

        if (this.settings.SessionEnable) {
            await this.refreshSession();
        }

        await this.setDateAndTime();
        await this.checkStatusAndVerifyIfNeeded();

        const { xmlResponse } = await this.sendXmlRequest(XML_REQUESTS.getInventory, [
            // Option Type 2 = 'Payable' inventory, see p76 of the IF Specification document
            { name: "Option", attributes: { type: "2" } },
        ]);
        this.inventoryChangeHandler(xmlResponse);
    }

    get status() {
        return GLORY_STATUS_STRING[this.state.status] ?? this.state.status;
    }

    get paymentLine() {
        const order = this.pos.getOrder();
        if (!order) {
            return null;
        }

        const gloryPaymentLines = order.payment_ids.filter(
            (line) => line.payment_method_id === this.payment_method_id
        );

        return gloryPaymentLines.find((line) =>
            ["waiting", "waitingCancel"].includes(line.payment_status)
        );
    }

    getDenominationsWithStatus(status) {
        return this.state.inventory.filter((denomination) => denomination.status === status);
    }

    newSequenceNumber() {
        this.sequenceNumber = uuidv4().replace("-", "").slice(0, 11);
    }

    statusChangeHandler(statusResponse, firstStatus = false) {
        const statusCodeElement =
            statusResponse.getElementsByTagName("Code")[0] ??
            statusResponse.getElementsByTagName("Status")[0];

        this.state.status = GLORY_STATUS[statusCodeElement.textContent];

        if (this.state.status === "WAITING_ERROR_RECOVERY") {
            this.showError(
                _t("The cash machine has an error, please consult its display for details.")
            );
            return;
        }

        if (!this.paymentLine) {
            return;
        }

        switch (this.state.status) {
            case "IDLE": {
                if (firstStatus) {
                    // In this case we have a stale payment
                    this.pos.getOrder().removePaymentline(this.paymentLine);
                }
                break;
            }
            case "COUNTING": {
                const amount = statusResponse.getElementsByTagName("Amount")[0].textContent;
                this.state.amountInserted = this.gloryAmountToPosAmount(amount);
                break;
            }
            case "WAITING_CANCEL": {
                this.showCancelDialog(
                    _t(
                        "There is insufficient change in the cash machine to handle the payment. It must be cancelled to continue."
                    )
                );
                break;
            }
            default: {
                if (this.settings.OccupyEnable && !this.occupied) {
                    this.occupy();
                }
            }
        }
    }

    parseGloryCashElement(cashElement) {
        const denominationElements = Array.from(cashElement.getElementsByTagName("Denomination"));
        return denominationElements.map((denomination) => ({
            value: this.gloryAmountToPosAmount(denomination.getAttribute("fv")),
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
    getTotalFromGloryCashElement(cashElement) {
        const denominations = this.parseGloryCashElement(cashElement);
        return this.env.utils.roundCurrency(
            denominations.reduce((total, next) => total + next.amount * next.value, 0)
        );
    }

    inventoryChangeHandler(inventoryResponse) {
        const cashElements = Array.from(inventoryResponse.getElementsByTagName("Cash"));
        const dispensableCash = cashElements.find(
            (cashElement) => cashElement.getAttribute("type") === "4"
        );
        if (!dispensableCash) {
            return;
        }

        const denominations = this.parseGloryCashElement(dispensableCash);
        this.state.inventory = sortBy(denominations, "value");
    }

    async sendPaymentRequest() {
        if (!this.paymentLine) {
            return false;
        }

        if (this.paymentLine.amount < 0 && this.pos.getCashier()._role !== "manager") {
            this.showError(_t("Only managers can withdraw cash from the cash machine."));
            return false;
        }

        if (
            this.socketIo.closed ||
            ["DISCONNECTED", "BAD_CREDENTIALS"].includes(this.state.status)
        ) {
            this.showError(_t("The cash machine is disconnected."));
            return false;
        }
        if (this.state.status === "ERROR" || this.state.status === "WAITING_ERROR_RECOVERY") {
            this.showError(
                _t("The cash machine has an error, please consult its display for details.")
            );
            return false;
        }
        if (this.state.status === "COLLECTING" || this.state.status === "WAITING_REPLENISHMENT") {
            this.showError(
                _t(
                    "The cash machine is currently in collection/replenishment mode, please finish this process on the machine before making a payment."
                )
            );
            return false;
        }

        if (this.settings.OccupyEnable) {
            await this.occupy();
        }

        this.state.amountInserted = 0;
        const amountString = Math.round(
            this.paymentLine.amount * Math.pow(10, this.pos.currency.decimal_places)
        ).toString(10);
        this.newSequenceNumber();

        const { xmlResponse } = await this.sendXmlRequest(XML_REQUESTS.startPayment, [
            {
                name: "Amount",
                children: [amountString],
            },
            {
                // Option Type 1 = Enable cancellation when there is insufficient change
                name: "Option",
                attributes: { type: "1" },
            },
        ]);

        const result = await this.handlePaymentResponse(xmlResponse);

        if (this.occupied) {
            await this.release();
        }

        if (this.cancellationResolver) {
            this.cancellationResolver();
            this.cancellationResolver = null;
        }

        return result;
    }

    /**
     * @param {Element} paymentResponse
     * @returns {Promise<boolean>}
     */
    async handlePaymentResponse(paymentResponse) {
        if (!this.paymentLine) {
            console.warn("Glory payment response received, but no payment in progress");
            return false;
        }

        switch (parseGloryResult(paymentResponse)) {
            case "SUCCESS": {
                this.setPaymentInfo(paymentResponse, true);
                return true;
            }
            case "CHANGE_SHORTAGE":
                this.setPaymentInfo(paymentResponse, false);
                await this.pos.printReceipt({ printBillActionTriggered: true });
                this.showError(_t("There is insufficient cash in the machine to give change."));
                return false;
            case "OCCUPIED_BY_OTHER":
                this.showError(_t("The cash machine is in use by another POS."));
                return false;
            case "EXCLUSIVE_ERROR": {
                this.showCancelDialog(
                    _t("The cash machine is busy with another operation. Do you want to cancel it?")
                );
                return false;
            }
            case "AUTO_RECOVERY_FAILURE": {
                this.showError(
                    _t(
                        "The payment failed due to an unrecoverable error - see the cash machine screen for details."
                    )
                );
                return false;
            }
            default:
                return false;
        }
    }

    async sendPaymentCancel() {
        if (this.socketIo.closed) {
            this.showError(_t("The cash machine is disconnected."));
            return false;
        }

        await this.sendXmlRequest(XML_REQUESTS.cancelPayment);

        const cancelPromise = new Promise((resolve) => {
            this.cancellationResolver = resolve;
        });
        return await cancelPromise;
    }

    /**
     * @param {Element} paymentResponse
     * @param {boolean} isSuccessful
     */
    setPaymentInfo(paymentResponse, isSuccessful) {
        const cashElements = Array.from(paymentResponse.getElementsByTagName("Cash"));
        const cashGivenElement = cashElements.find(
            (cashElement) => cashElement.getAttribute("type") === "1"
        );
        const cashReturnedElement = cashElements.find(
            (cashElement) => cashElement.getAttribute("type") === "2"
        );
        const cashGiven = this.getTotalFromGloryCashElement(cashGivenElement);
        const cashReturned = this.getTotalFromGloryCashElement(cashReturnedElement);
        const transactionId = paymentResponse.getElementsByTagName("TransactionId")[0].textContent;

        this.paymentLine.transaction_id = transactionId;
        this.paymentLine.setAmount(cashGiven);
        this.paymentLine.setReceiptInfo(
            this.makeReceiptMessage(transactionId, cashGiven, cashReturned, isSuccessful)
        );
    }

    /**
     * @param {string} transactionId
     * @param {number} amountDeposited
     * @param {number} amountReturned
     * @param {boolean} isSuccessful
     * @returns {string}
     */
    makeReceiptMessage(transactionId, amountDeposited, amountReturned, isSuccessful) {
        const header = isSuccessful
            ? _t("GLORY TRANSACTION SUCCESSFUL")
            : _t("GLORY TRANSACTION CANCELLED");
        const transactionIdLine = _t("Transaction ID: %s", transactionId);
        const depositedLine = _t(
            "Cash deposited: %s",
            this.env.utils.formatCurrency(amountDeposited)
        );
        const changeGivenLine = _t(
            "Change given: %s",
            this.env.utils.formatCurrency(amountReturned)
        );

        return `${header}\n${transactionIdLine}\n${depositedLine}\n${changeGivenLine}\n\n`;
    }

    async setDateAndTime() {
        const now = DateTime.now();
        await this.sendXmlRequest(XML_REQUESTS.setDateAndTime, [
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

    async refreshSession() {
        const data = await this.sendWebsocketRequest(WEBSOCKET_REQUESTS.openSession);
        this.sessionId = data.SessionID;
    }

    async occupy() {
        await this.sendXmlRequest(XML_REQUESTS.occupy);
        this.occupied = true;
    }

    async release() {
        await this.sendXmlRequest(XML_REQUESTS.release);
        this.occupied = false;
    }

    sendWebsocketRequest(request, ...params) {
        this.socketIo.sendMessage([request.requestName, ...params]);
        return this.waitForResponseWithType(request.responseName);
    }

    async waitForResponseWithType(type) {
        const responsePromise = new Promise((resolve) => {
            this.resolvers[type] = resolve;
        });
        const result = await responsePromise;
        this.resolvers[type] = null;
        return result;
    }

    /**
     * @param {import("models").GloryRequestInfo} request
     * @param {import("models").GloryXmlElement[]?} children
     */
    async sendXmlRequest(request, children, secondAttempt = false) {
        const xmlElement = {
            name: request.requestName,
            children: [
                ...makeGloryHeader(this.sequenceNumber, this.sessionId),
                ...(children ?? []),
            ],
        };
        const xmlString = serializeGloryXml(xmlElement);
        this.logXml("SEND", xmlString);
        this.socketIo.sendMessage(["xml send", xmlString]);

        const xmlResponse = await this.waitForResponseWithType(request.responseName);
        const statusCode = parseGloryResult(xmlResponse);

        if (
            !secondAttempt &&
            (statusCode === "SESSION_TIMEOUT" || statusCode === "INVALID_SESSION")
        ) {
            await this.refreshSession();
            return this.sendXmlRequest(request, children, true);
        }

        return { statusCode, xmlResponse };
    }

    gloryAmountToPosAmount(amountStringInCents) {
        const amountInCents = parseInt(amountStringInCents);
        const amount = amountInCents / Math.pow(10, this.pos.currency.decimal_places);
        return this.env.utils.roundCurrency(amount);
    }

    showError(msg, title) {
        if (!title) {
            title = _t("Cash Machine Error");
        }
        this.dialog.add(AlertDialog, {
            title: title,
            body: msg,
        });
    }

    showCancelDialog(message) {
        this.dialog.add(CancelDialog, {
            message,
            cancel: async () => {
                if (this.settings.OccupyEnable && !this.occupied) {
                    await this.occupy();
                }

                const { statusCode } = await this.sendXmlRequest(XML_REQUESTS.cancelPayment);
                if (statusCode !== "SUCCESS") {
                    await this.reset(true);
                }

                if (this.occupied) {
                    await this.release();
                }
            },
        });
    }
}
