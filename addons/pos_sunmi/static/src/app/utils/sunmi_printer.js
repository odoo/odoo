import { BasePrinter } from "@point_of_sale/app/utils/printer/base_printer";
import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";
import { _t } from "@web/core/l10n/translation";

const CONSOLE_COLOR = "#28ffeb";

/* global SUNMI */
export class SunmiPrinterAdapter extends BasePrinter {
    setup({ printer } = {}) {
        if (typeof SUNMI === "undefined") {
            throw new Error("SUNMI global object is not available. Ensure the Sunmi printer SDK is loaded.");
        }
        super.setup(...arguments);
        this.sunmiPrinter = new SUNMI();
        this.isConnected = false;
        this.printer = printer;
        const {
            TextStyle,
            BarcodeStyle,
            QrStyle,
            BitmapStyle,
            AreaStyle,
            LabelStyle,
        } = this.sunmiPrinter.class;
        this.BitmapStyle = BitmapStyle;
    }

    isConnected() {
        return this.sunmiPrinter.connected;
    }

    async printerStatus() {
        try {
            return await this.getStatus();
        } catch (error) {
            logPosMessage(
                "SunmiPrinterAdapter",
                "printerStatus",
                "Failed to get printer status: " + error.message,
                CONSOLE_COLOR,
                [error]
            );
            return { value: -1 };
        }
    }

    async launchPrintService() {
        let retries = 3;
        while (retries > 0) {
            try {
                await this.sunmiPrinter.launchPrinterService();
                await this.sunmiPrinter.init();
                this.isConnected = true;
                return;
            } catch (error) {
                retries -= 1;
                console.warn(`Retrying Sunmi printer initialization (${3 - retries}/3)...`);
                if (retries === 0) {
                    throw new Error("Failed to initialize Sunmi printer after 3 attempts: " + error.message);
                }
                await new Promise((resolve) => setTimeout(resolve, 1000)); // Wait 1 second before retrying
            }
        }
    }

    async getStatus() {
        try {
            const res = await this.sunmiPrinter.printer.queryApi.getStatus();
            return res.status.includes("READY") ? { value: 0 } : { value: -1 };
        } catch (error) {
            console.log("Error:" + error)
            return false;
        }
    }

    getInfo() {
        this.sunmiPrinter.printer.queryApi.getInfo(sunmiPrinter.ENUM.PrinterInfo.ID)
            .then((res) => {
                const data = JSON.stringify(res);
            });
    }

    async renderBitmap(bitmap) {
        var bitmap = bitmap.replace(/^data:.+;base64,/, "");
        try {
            const res = await this.sunmiPrinter.printer.canvasApi.renderBitmap(bitmap);
            // const res = await this.sunmiPrinter.printer.canvasApi.renderBitmap(bitmap, this.BitmapStyle.getStyle().setPosY(110));
        } catch (error) {
            console.log("error: " + error);
            return false;
        }
    }

    async printBitmap(bitmap) {
        var bitmap = bitmap.replace(/^data:.+;base64,/, "");
        await this.sunmiPrinter.printer.lineApi.printBitmap(bitmap, this.BitmapStyle.getStyle().setAlign("CENTER"));
    }


    /**
     * @override
     */
    // convert canvas into jpeg image to print
    processCanvas(canvas) {
        return canvas.toDataURL("image/jpeg");
    }

    /**
     * @override
     */
    async sendPrintingJob(img) {
        try {
            const status = await this.printerStatus();
            if (status.value !== 0) {
                return { result: false, errorCode: status.value, canRetry: true };
            }
            const processedImg = this.processCanvas(img);
            await this.printBitmap(processedImg);
            this.sunmiPrinter.printer.lineApi.autoOut();
            return { result: true };
            // potential improvement: add retries for failed attempts
        } catch (error) {
            console.error("Error print job failed: " + error);
            logPosMessage(
                "SunmiPrinterAdapter",
                "sendPrintingJob",
                "Printing job failed: " + error.message,
                CONSOLE_COLOR,
                [error]
            );
            return { result: false, errorCode: error.message, canRetry: true };
        }
    }
}
