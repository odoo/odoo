import { _t } from "@web/core/l10n/translation";
import { BasePrinter } from "@point_of_sale/app/utils/printer/base_printer";

const ERROR_MESSAGES = {
    PRINTER_NOT_FOUND: {
        title: _t("Printer Not Found"),
        body: _t("No printer is available. Please check printer connection and try again."),
    },
    CONNECTION_FAILED: {
        title: _t("Connection Failed"),
        body: _t("Failed to connect to printer service."),
    },
    PRINT_FAILED: {
        title: _t("Printing Failed"),
        body: _t("Failed to print. Please check printer connection and try again."),
    },
};

export class OdooLocalPrinter extends BasePrinter {
    async setup({ printer }) {
        super.setup(...arguments);
        this.odooNativeApp = window.OdooNativeApp;
        this.printer = printer.local_printer_data || {};
    }

    async openCashbox() {
        await this._execute("cash_drawer");
    }

    async sendPrintingJob(image) {
        return this._execute("print_receipt", { image });
    }

    async _execute(action, data = {}) {
        try {
            const response = await this.odooNativeApp.action({
                action,
                device: JSON.parse(JSON.stringify(this.printer)),
                data,
            });

            if (response.status === true) {
                return {
                    result: true,
                    message: response.message || _t("Print job sent successfully"),
                    canRetry: false,
                };
            } else {
                return this._getErrorResult(response.error_code, "PRINT_FAILED");
            }
        } catch {
            return this._getErrorResult("CONNECTION_FAILED");
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
        actionError.message.body += _t(
            "Please check that the printer is turned on and connected, then try again."
        );
        return actionError;
    }

    getResultsError(printResult) {
        return printResult || this._getErrorResult("CONNECTION_FAILED");
    }
}
