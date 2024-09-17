import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
<<<<<<< saas-18.1:addons/point_of_sale/static/src/app/services/pos_printer_service.js
import { PrinterService } from "@point_of_sale/app/services/printer_service";
import { AlertDialog, ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
||||||| 69b404c7109ff689381f56520aad758424ec01aa:addons/point_of_sale/static/src/app/printer/pos_printer_service.js
import { PrinterService } from "@point_of_sale/app/printer/printer_service";
import { AlertDialog, ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
=======
import { PrinterService } from "@point_of_sale/app/printer/printer_service";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { ask } from "@point_of_sale/app/store/make_awaitable_dialog";
>>>>>>> f3f07012b8df310db66b3e6cf06ef5598346aadd:addons/point_of_sale/static/src/app/printer/pos_printer_service.js

export const posPrinterService = {
    dependencies: ["hardware_proxy", "dialog", "renderer"],
    start(env, { hardware_proxy, dialog, renderer }) {
        return new PosPrinterService(env, { hardware_proxy, dialog, renderer });
    },
};
export class PosPrinterService extends PrinterService {
    constructor(...args) {
        super(...args);
        this.setup(...args);
    }
    setup(env, { hardware_proxy, dialog, renderer }) {
        super.setup(...arguments);
        this.renderer = renderer;
        this.hardware_proxy = hardware_proxy;
        this.dialog = dialog;
        this.device = hardware_proxy.printer;
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
        this.setPrinter(this.hardware_proxy.printer);
        try {
            return await super.printHtml(...arguments);
        } catch (error) {
            return this.printHtmlAlternative(error);
        }
    }
    async printHtmlAlternative(error) {
        const confirmed = await ask(this.dialog, {
            title: error.title || _t("Printing error"),
            body: error.body + _t("Do you want to print using the web printer? "),
        });
        if (confirmed) {
            // We want to call the _printWeb when the dialog is fully gone
            // from the screen which happens after the next animation frame.
            await new Promise(requestAnimationFrame);
            this.printWeb(...arguments);
        }
    }
}

registry.category("services").add("printer", posPrinterService);
