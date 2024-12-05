import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { PrinterService } from "@point_of_sale/app/services/printer_service";
import { AlertDialog, ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

const posPrinterService = {
    dependencies: ["hardware_proxy", "dialog", "renderer"],
    start(env, { hardware_proxy, dialog, renderer }) {
        return new PosPrinterService(env, { hardware_proxy, dialog, renderer });
    },
};
class PosPrinterService extends PrinterService {
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
<<<<<<< master:addons/point_of_sale/static/src/app/services/pos_printer_service.js
            this.dialog.add(ConfirmationDialog, {
                title: error.title || _t("Printing error"),
                body: error.body + _t("Do you want to print using the web printer? "),
                confirm: async () => {
                    // We want to call the _printWeb when the dialog is fully gone
                    // from the screen which happens after the next animation frame.
                    await new Promise(requestAnimationFrame);
                    this.printWeb(...arguments);
                },
            });
||||||| 5c10f9b4c62c22473e2b1d0d11c6ee265e4a9248:addons/point_of_sale/static/src/app/printer/pos_printer_service.js
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
=======
            return this.printHtmlAlternative(error, ...arguments);
        }
    }
    async printHtmlAlternative(error, ...printArguments) {
        const confirmed = await ask(this.dialog, {
            title: error.title || _t("Printing error"),
            body: error.body + _t("Do you want to print using the web printer? "),
        });
        if (confirmed) {
            // We want to call the _printWeb when the dialog is fully gone
            // from the screen which happens after the next animation frame.
            await new Promise(requestAnimationFrame);
            this.printWeb(...printArguments);
>>>>>>> f2475c2e40b0cfb6cde47e814bc0d75f9265c8a5:addons/point_of_sale/static/src/app/printer/pos_printer_service.js
        }
    }
}

registry.category("services").add("printer", posPrinterService);
