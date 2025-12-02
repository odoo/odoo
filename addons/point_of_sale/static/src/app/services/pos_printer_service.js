import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { RetryPrintPopup } from "@point_of_sale/app/components/popups/retry_print_popup/retry_print_popup";
import { PrinterService } from "@point_of_sale/app/services/printer_service";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { logPosMessage } from "../utils/pretty_console_log";

export const posPrinterService = {
    dependencies: ["dialog", "renderer"],
    start(env, { dialog, renderer }) {
        return new PosPrinterService(env, { dialog, renderer });
    },
};
export class PosPrinterService extends PrinterService {
    constructor(...args) {
        super(...args);
        this.setup(...args);
    }
    setup(env, { dialog, renderer }) {
        super.setup(...arguments);
        this.renderer = renderer;
        this.dialog = dialog;
    }
    async print() {
        return super.print(...arguments);
    }
    printWeb() {
        try {
            return super.printWeb(...arguments);
        } catch {
            this.dialog.add(AlertDialog, {
                title: _t("Printing is not supported on some browsers"),
                body: _t("It is possible to print your tickets by making use of an IoT Box."),
            });
            return false;
        }
    }
    async printHtml() {
        try {
            return await super.printHtml(...arguments);
        } catch (error) {
            if (error.body === undefined) {
                logPosMessage(
                    "PosPrinterService",
                    "printHtml",
                    "An unknown error occured in printHtml",
                    false,
                    [error]
                );
            }

            this.dialog.closeAll();
            this.dialog.add(RetryPrintPopup, {
                title: error.title,
                message: error.body,
                canRetry: error.canRetry,
                retry: () => {
                    this.printHtml(...arguments);
                },
                download: () => {
                    this.printWeb(...arguments);
                },
            });
        }
    }
}

registry.category("services").add("printer", posPrinterService);
