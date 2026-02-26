import { BasePrinter } from "@point_of_sale/app/utils/printer/base_printer";
import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";

const CONSOLE_COLOR = "#28ffeb";
const WEBSOCKET_URL = "ws://localhost:7070/ws";

/* global SUNMI */
export class SunmiPrinterAdapter extends BasePrinter {
    setup({ fallbackPrinter } = {}) {
        super.setup(...arguments);
        this.sunmiPrinter = new SUNMI();
        this.fallbackPrinter = fallbackPrinter;
        this.isConnected = false;
    }

    async connect() {
        await this.sunmiPrinter.init();
        this.isConnected = true;
    }

    async isAvailable() {
        await this.sunmiPrinter.launchPrinterService();
        return new Promise((resolve) => {
            try {
                const timer = setTimeout(() => {
                    ws.close();
                    resolve(false);
                }, 3000);
                const ws = new window.WebSocket(WEBSOCKET_URL);
                ws.onopen = function () {
                    clearTimeout(timer);
                    ws.close();
                    resolve(true);
                };
                ws.onerror = function () {
                    clearTimeout(timer);
                    resolve(false);
                };
            } catch (error) {
                logPosMessage(
                    "SunmiPrinterAdapter",
                    "isAvailable",
                    "Error checking printer availability: " + error.message,
                    CONSOLE_COLOR,
                    [error]
                );
                resolve(false);
            }
        });
    }

    async printerStatus() {
        if (!this.isConnected) {
            return { status: "NOT_CONNECTED" };
        }
        try {
            const res = await this.sunmiPrinter.printer.queryApi.getStatus();
            res.status = res.status.slice(1, -1);
            return res;
        } catch (error) {
            logPosMessage(
                "SunmiPrinterAdapter",
                "printerStatus",
                "Failed to get printer status: " + error.message,
                CONSOLE_COLOR,
                [error]
            );
            return { status: "UNKNOWN" };
        }
    }

    /**
     * @override
     */
    processCanvas(canvas) {
        return canvas.toDataURL("image/jpeg");
    }

    /**
     * @override
     */
    async printReceipt(receipt) {
        const res = await this.printerStatus();
        // We only use the fallback printer if the printer is not connected or not powered on
        if (res.status !== "READY" && this.fallbackPrinter) {
            return await this.fallbackPrinter.printReceipt(receipt);
        }
        return await super.printReceipt(receipt);
    }

    /**
     * @override
     */
    async sendPrintingJob(img) {
        try {
            const res = await this.printerStatus();
            if (res.status !== "READY") {
                return { result: false, errorCode: res.status, canRetry: true };
            }

            const { lineApi } = this.sunmiPrinter.printer;
            const { BitmapStyle } = this.sunmiPrinter.class;

            const base64Data = img.replace(/^data:.+;base64,/, "");
            const printStyle = new BitmapStyle().setAlign("CENTER");

            await lineApi.printBitmap(base64Data, printStyle);
            lineApi.autoOut();

            return { result: true };
        } catch (error) {
            logPosMessage(
                "SunmiPrinterAdapter",
                "sendPrintingJob",
                `Printing job failed: ${error.message}`,
                CONSOLE_COLOR,
                [error]
            );

            return { result: false, errorCode: error.message, canRetry: true };
        }
    }
}
