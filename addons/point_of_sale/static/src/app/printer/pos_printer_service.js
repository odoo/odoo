/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { PrinterService } from "@point_of_sale/app/printer/printer_service";
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
<<<<<<< saas-17.1
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
||||||| 866dbb18403d9d9a0fd79a12677838c18958d1a9
            return this.printHtmlAlternative(error);
=======
            return this.printHtmlAlternative(error, ...arguments);
>>>>>>> 8ea0b125921b1cd2d9552a11f2600c5056484662
        }
    }
<<<<<<< saas-17.1
||||||| 866dbb18403d9d9a0fd79a12677838c18958d1a9
    async printHtmlAlternative(error) {
        const { confirmed } = await this.popup.add(ConfirmPopup, {
            title: error.title || _t("Printing error"),
            body: error.body + _t("Do you want to print using the web printer? "),
        });
        if (!confirmed) {
            return false;
        }
        // We want to call the _printWeb when the popup is fully gone
        // from the screen which happens after the next animation frame.
        await new Promise(requestAnimationFrame);
        return this.printWeb(...arguments);
    }
=======
    async printHtmlAlternative(error, ...args) {
        const { confirmed } = await this.popup.add(ConfirmPopup, {
            title: error.title || _t("Printing error"),
            body: error.body + _t("Do you want to print using the web printer? "),
        });
        if (!confirmed) {
            return false;
        }
        // We want to call the _printWeb when the popup is fully gone
        // from the screen which happens after the next animation frame.
        await new Promise(requestAnimationFrame);
        return this.printWeb(...args);
    }
>>>>>>> 8ea0b125921b1cd2d9552a11f2600c5056484662
}

registry.category("services").add("printer", posPrinterService);
