/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { PrinterService } from "@point_of_sale/app/printer/printer_service";
import { AlertDialog, ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

<<<<<<< HEAD
const posPrinterService = {
    dependencies: ["hardware_proxy", "dialog", "renderer"],
    start(env, { hardware_proxy, dialog, renderer }) {
        return new PosPrinterService(env, { hardware_proxy, dialog, renderer });
||||||| parent of 79351a23bdf8 (temp)
const posPrinterService = {
    dependencies: ["hardware_proxy", "popup", "renderer"],
    start(env, { hardware_proxy, popup, renderer }) {
        return new PosPrinterService(env, { hardware_proxy, popup, renderer });
=======
export const posPrinterService = {
    dependencies: ["hardware_proxy", "popup", "renderer", "pos"],
    start(env, { hardware_proxy, popup, renderer, pos }) {
        return new PosPrinterService(env, { hardware_proxy, popup, renderer, pos });
>>>>>>> 79351a23bdf8 (temp)
    },
};
export class PosPrinterService extends PrinterService {
    constructor(...args) {
        super(...args);
        this.setup(...args);
    }
<<<<<<< HEAD
    setup(env, { hardware_proxy, dialog, renderer }) {
        super.setup(...arguments);
||||||| parent of 79351a23bdf8 (temp)
    setup(env, { hardware_proxy, popup, renderer }) {
=======
    setup(env, { hardware_proxy, popup, renderer, pos }) {
>>>>>>> 79351a23bdf8 (temp)
        this.renderer = renderer;
        this.hardware_proxy = hardware_proxy;
        this.dialog = dialog;
        this.device = hardware_proxy.printer;
        this.pos = pos;
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
<<<<<<< HEAD
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
||||||| parent of 79351a23bdf8 (temp)
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
            return await this.printWeb(...arguments);
=======
            return this.printHtmlAlternative(error);
>>>>>>> 79351a23bdf8 (temp)
        }
    }
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
}

registry.category("services").add("printer", posPrinterService);
