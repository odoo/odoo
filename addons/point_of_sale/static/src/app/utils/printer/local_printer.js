import { _t } from "@web/core/l10n/translation";
import { BasePrinter } from "@point_of_sale/app/utils/printer/base_printer";

const ERROR_MESSAGES = {
    PRINTER_NOT_FOUND: {
        title: _t("Printer Not Found"),
        body: _t("No printer is detected. Please check the printer connection and try again."),
    },
    CONNECTION_FAILED: {
        title: _t("Connection Failed"),
        body: _t(
            "Unable to connect to the printer. Please check the printer connection and try again."
        ),
    },
    PRINT_FAILED: {
        title: _t("Printing Failed"),
        body: _t("Failed to print. Please check the printer connection and try again."),
    },
};

export class OdooLocalPrinter extends BasePrinter {
    async setup() {
        super.setup(...arguments);
        this.odooNativeApp = window.OdooNativeApp;
    }

    async openCashbox() {
        return this._sendPrintingJob("", true);
    }

    async sendPrintingJob(printData) {
        return this._sendPrintingJob(printData);
    }

    async _sendPrintingJob(printData = "", openCashBox) {
        try {
            const response = await this.odooNativeApp.printReceipt({
                receipt: printData,
                cash_drawer: openCashBox,
            });
            if (response.status === true) {
                return {
                    result: true,
                    canRetry: false,
                };
            } else {
                return this._getErrorResult(response.error_code, "PRINT_FAILED");
            }
        } catch {
            return this._getErrorResult();
        }
    }

    _getErrorResult(errorCode, defaultCode = "CONNECTION_FAILED") {
        const message = ERROR_MESSAGES[errorCode] || ERROR_MESSAGES[defaultCode];
        return {
            result: false,
            errorCode,
            canRetry: true,
            message: {
                title: message.title,
                body: message.body,
            },
        };
    }

    getActionError() {
        const actionError = super.getResultsError();
        actionError.message.body = _t(
            "Please make sure the printer is turned on and properly connected, then try again."
        );
        return actionError;
    }

    getResultsError(printResult) {
        return printResult || this._getErrorResult();
    }
}
