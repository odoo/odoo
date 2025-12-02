import { _t } from "@web/core/l10n/translation";
import { ConnectionLostError } from "@web/core/network/rpc";
import { htmlToCanvas } from "@point_of_sale/app/services/render_service";
/**
 * Implements basic printer functions.
 */
export class BasePrinter {
    constructor() {
        this.setup(...arguments);
    }

    setup() {
        this.receiptQueue = [];
    }

    /**
     * Add the receipt to the queue of receipts to be printed and process it.
     * We clear the print queue if printing is not successful.
     * @param {String} receipt: The receipt to be printed, in HTML
     * @returns {{ successful: boolean; message?: { title: string; body?: string }}}
     */
    async printReceipt(receipt) {
        if (receipt) {
            this.receiptQueue.push(receipt);
        }
        let image, printResult;
        while (this.receiptQueue.length > 0) {
            receipt = this.receiptQueue.shift();
            image = this.processCanvas(
                await htmlToCanvas(receipt, { addClass: "pos-receipt-print" })
            );
            try {
                printResult = await this.sendPrintingJob(image);
            } catch (error) {
                // Error in communicating to the IoT box.
                this.receiptQueue.length = 0;
                if (error instanceof ConnectionLostError) {
                    return this.getOfflineError();
                }
                return this.getActionError();
            }
            // rpc call is okay but printing failed because
            // IoT box can't find a printer.
            if (!printResult || printResult.result === false) {
                this.receiptQueue.length = 0;
                return this.getResultsError(printResult);
            }
        }
        return {
            successful: true,
            warningCode: this.getResultWarningCode(printResult),
        };
    }

    async sendPrintingJob() {
        throw new Error("Not implemented");
    }

    openCashbox() {
        throw new Error("Not implemented");
    }

    /**
     * Generate a jpeg image from a canvas
     * @param {DOMElement} canvas
     */
    processCanvas(canvas) {
        return canvas.toDataURL("image/jpeg").replace("data:image/jpeg;base64,", "");
    }

    /**
     * Return value of this method will be the result of calling `printReceipt`
     * if it failed to connect to the IoT box.
     */
    getActionError() {
        return {
            successful: false,
            canRetry: true,
            message: {
                title: _t("Connection to IoT Box failed"),
                body: _t(
                    "Please ensure the IoT box is turned on and connected to the network before retrying."
                ),
            },
        };
    }

    /**
     * Return value of this method will be the result of calling `printReceipt`
     * if it failed due to the client being offline.
     */
    getOfflineError() {
        return {
            successful: false,
            canRetry: true,
            message: {
                title: _t("No Internet Connection"),
                body: _t("Please ensure you are connected to the internet before retrying."),
            },
        };
    }

    /**
     * Return value of this method will be the result of calling `printReceipt`
     * if the result coming from the IoT box is empty.
     */
    getResultsError(_printResult) {
        return {
            successful: false,
            canRetry: true,
            message: {
                title: _t("Connection to the printer failed"),
                body: _t(
                    "Your IoT box cannot find the printer, please ensure it is connected and turned on before retrying."
                ),
            },
        };
    }

    getResultWarningCode(_printResult, options = {}) {
        return undefined;
    }
}
