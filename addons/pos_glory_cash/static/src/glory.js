import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { uuidv4 } from "@point_of_sale/utils";
import { CancelDialog } from "@pos_glory_cash/app/components/cancel_dialog";
import { serializeGloryXml, parseGloryXml, makeGloryHeader } from "@pos_glory_cash/utils/glory_xml";
import {
    GLORY_RESULT,
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

const { DateTime } = luxon;

const WEBSOCKET_PORT = browser.location.protocol === "https:" ? 3001 : 3000;
const WEBSOCKET_PROTOCOL = browser.location.protocol === "https:" ? "wss:" : "ws:";
const WEBSOCKET_URL = "/socket.io/?transport=websocket&EIO=3";

export class GloryService extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        this.dialog = this.env.services.dialog;

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
            onEvent: ([responseType, data]) => {
                if (this.resolvers[responseType]) {
                    this.resolvers[responseType](data);
                }
            },
            onBinaryEvent: (data) =>
                parseGloryXml(data).then((response) => {
                    const message = response.firstChild;
                    if (this.resolvers[message.tagName]) {
                        this.resolvers[message.tagName](message);
                    } else if (this.eventHandlers[message.tagName]) {
                        this.eventHandlers[message.tagName](message);
                    }
                }),
        });
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
        this.waitForResponseWithType("credential ng").then(
            () => (this.state.status = "BAD_CREDENTIALS")
        );
        await this.sendWebsocketRequest(
            WEBSOCKET_REQUESTS.checkCredentials,
            this.gloryUser?.session_id
        );
    }

    async onConnect() {
        await this.login();

        const settings = await this.sendWebsocketRequest(WEBSOCKET_REQUESTS.getSettings);
        this.settings = settings.FunctionSetting;

        if (this.settings.SessionEnable) {
            await this.refreshSession();
        }

        await this.setDateAndTime();

        const initialStatus = await this.sendXmlRequest(XML_REQUESTS.getStatus);
        this.statusChangeHandler(initialStatus, true);

        const initialInventory = await this.sendXmlRequest(XML_REQUESTS.getInventory, [
            // Option Type 2 = 'Payable' inventory, see p76 of the IF Specification document
            { name: "Option", attributes: { type: "2" } },
        ]);
        this.inventoryChangeHandler(initialInventory);
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

    inventoryChangeHandler(inventoryResponse) {
        const cashElements = Array.from(inventoryResponse.getElementsByTagName("Cash"));
        const dispensableCash = cashElements.find(
            (cashElement) => cashElement.getAttribute("type") === "4"
        );
        if (!dispensableCash) {
            return;
        }

        const denominationElements = Array.from(
            dispensableCash.getElementsByTagName("Denomination")
        );
        const denominations = denominationElements.map((denomination) => ({
            value: this.gloryAmountToPosAmount(denomination.getAttribute("fv")),
            amount: denomination.getElementsByTagName("Piece")[0].textContent,
            status: GLORY_CURRENCY_STATUS[
                denomination.getElementsByTagName("Status")[0].textContent
            ],
        }));
        this.state.inventory = sortBy(denominations, "value");
    }

    async sendPaymentRequest() {
        if (!this.paymentLine) {
            return false;
        }

        if (this.paymentLine.amount < 0 && this.pos.getCashier().role !== "manager") {
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

        if (this.settings.OccupyEnable) {
            await this.occupy();
        }

        this.state.amountInserted = 0;
        const amountString = Math.round(this.paymentLine.amount * 100).toString(10);
        this.newSequenceNumber();

        const paymentResponse = await this.sendXmlRequest(XML_REQUESTS.startPayment, [
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

        if (this.cancellationResolver) {
            this.cancellationResolver();
            this.cancellationResolver = null;
        }

        const result = await this.handlePaymentResponse(paymentResponse);

        if (this.occupied) {
            await this.release();
        }

        return result;
    }

    async handlePaymentResponse(paymentResponse) {
        if (!this.paymentLine) {
            console.warn("Glory payment response received, but no payment in progress");
            return false;
        }

        const paymentStatus = GLORY_RESULT[paymentResponse.getAttribute("result")];

        switch (paymentStatus) {
            case "SUCCESS": {
                this.paymentLine.setAmount(this.state.amountInserted);
                return true;
            }
            case "SESSION_TIMEOUT":
            case "INVALID_SESSION": {
                await this.refreshSession();
                return this.sendPaymentRequest();
            }
            case "CHANGE_SHORTAGE":
                this.paymentLine.setAmount(this.state.amountInserted);
                this.pos.printReceipt({ printBillActionTriggered: true });
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

        const cancelResponse = await this.sendXmlRequest(XML_REQUESTS.cancelPayment);

        const cancelStatus = GLORY_RESULT[cancelResponse.getAttribute("result")];
        if (cancelStatus === "SESSION_TIMEOUT" || cancelStatus === "INVALID_SESSION") {
            await this.refreshSession();
            return this.sendPaymentCancel();
        }

        const cancelPromise = new Promise((resolve) => {
            this.cancellationResolver = resolve;
        });
        return await cancelPromise;
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
    sendXmlRequest(request, children) {
        const xmlElement = {
            name: request.requestName,
            children: [
                ...makeGloryHeader(this.sequenceNumber, this.sessionId),
                ...(children ?? []),
            ],
        };
        const xmlString = serializeGloryXml(xmlElement);
        this.socketIo.sendMessage(["xml send", xmlString]);

        return this.waitForResponseWithType(request.responseName);
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

                const cancelResponse = await this.sendXmlRequest(XML_REQUESTS.cancelPayment);
                if (GLORY_RESULT[cancelResponse.getAttribute("result")] !== "SUCCESS") {
                    await this.sendXmlRequest(XML_REQUESTS.reset);
                }

                if (this.occupied) {
                    await this.release();
                }
            },
        });
    }
}
