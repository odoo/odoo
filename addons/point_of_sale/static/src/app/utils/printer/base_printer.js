import { _t } from "@web/core/l10n/translation";
import { ConnectionLostError } from "@web/core/network/rpc";

export class BasePrinter {
    constructor() {
        this.setup(...arguments);
    }

    setup({ printer }) {
        this.id = printer.id;
        this.name = printer.name;
        this.type = printer.type;
        this.product_categories_ids = printer.product_categories_ids;
        this.pos_config_ids = printer.pos_config_ids;
        this.use_lna = printer.use_lna;
    }

    async print(image) {
        try {
            const result = await this.sendPrintingJob(image);
            if (!result || result.result === false) {
                return this.getResultsError(result);
            }

            return {
                successful: true,
                warningCode: this.getResultWarningCode(result),
            };
        } catch (error) {
            let data = this.getActionError();
            if (error instanceof ConnectionLostError) {
                data = this.getOfflineError();
            }
            return data;
        }
    }

    async sendPrintingJob() {
        throw new Error("Not implemented");
    }

    openCashbox() {
        throw new Error("Not implemented");
    }

    /**
     * Return value of this method will be the result of calling `print`
     * if it failed to connect to the IoT box.
     */
    getActionError() {
        return {
            successful: false,
            canRetry: true,
            message: {
                title: _t("Connection to the printer failed"),
                body: _t(
                    "Please ensure the printer is turned on and connected to the network before retrying."
                ),
            },
        };
    }

    /**
     * Return value of this method will be the result of calling `print`
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
     * Return value of this method will be the result of calling `print`
     * if the result coming from the IoT box is empty.
     */
    getResultsError(_printResult) {
        return {
            successful: false,
            canRetry: true,
            message: {
                title: _t("Connection to the printer failed"),
                body: _t(
                    "Please ensure the printer is turned on and connected to the network before retrying."
                ),
            },
        };
    }

    getResultWarningCode(_printResult, options = {}) {
        return undefined;
    }
}
