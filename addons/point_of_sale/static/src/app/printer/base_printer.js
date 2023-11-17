/* @odoo-module */
/* global html2canvas */

import { _t } from "@web/core/l10n/translation";

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
            image = await this.htmlToImg(receipt);
            try {
                printResult = await this.sendPrintingJob(image);
            } catch {
                // Error in communicating to the IoT box.
                this.receiptQueue.length = 0;
                return this.getActionError();
            }
            // rpc call is okay but printing failed because
            // IoT box can't find a printer.
            if (!printResult || printResult.result === false) {
                this.receiptQueue.length = 0;
                return this.getResultsError(printResult);
            }
        }
        return { successful: true };
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
     * This function renders `el` as an image for printing assuming the following
     * - a `div.pos-receipt-print` is present in the dom and will serve as the container
     * - a `.pos-receipt` is the root element of `el`.
     * @param {HTMLElement} el The element to be converted as image
     * @returns {HTMLCanvasElement}
     */
    async htmlToImg(el) {
        const elClone = el.cloneNode(true);
        const receiptContainer = document.querySelector(".pos-receipt-print");
        receiptContainer.appendChild(elClone);
        const receipt = elClone;
        // Odoo RTL support automatically flip left into right but html2canvas
        // won't work as expected if the receipt is aligned to the right of the
        // screen so we need to flip it back.
        const parent = receipt.parentElement;
        parent.style.left = 0;
        parent.style.right = "auto";
        const canvas = await html2canvas(receipt, {
            height: Math.ceil(receipt.clientHeight),
            width: Math.ceil(receipt.clientWidth),
            scale: 1,
        });
        receipt.remove();
        return this.processCanvas(canvas);
    }

    /**
     * Return value of this method will be the result of calling `printReceipt`
     * if it failed to connect to the IoT box.
     */
    getActionError() {
        return {
            successful: false,
            message: {
                title: _t("Connection to IoT Box failed"),
                body: _t("Please check if the IoT Box is still connected."),
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
            message: {
                title: _t("Connection to the printer failed"),
                body: _t(
                    "Please check if the printer is still connected. \n" +
                        "Some browsers don't allow HTTP calls from websites to devices in the network (for security reasons). " +
                        "If it is the case, you will need to follow Odoo's documentation for " +
                        "'Self-signed certificate for ePOS printers' and 'Secure connection (HTTPS)' to solve the issue"
                ),
            },
        };
    }
}
