/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { ConfirmPopup } from "@point_of_sale/app/utils/confirm_popup/confirm_popup";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { PrinterService } from "@point_of_sale/app/printer/printer_service";

export const posPrinterService = {
    dependencies: ["hardware_proxy", "popup", "renderer", "pos"],
    start(env, { hardware_proxy, popup, renderer, pos }) {
        return new PosPrinterService(env, { hardware_proxy, popup, renderer, pos });
    },
};
export class PosPrinterService extends PrinterService {
    constructor(...args) {
        super(...args);
        this.setup(...args);
    }
    setup(env, { hardware_proxy, popup, renderer, pos }) {
        this.renderer = renderer;
        this.hardware_proxy = hardware_proxy;
        this.popup = popup;
        this.device = hardware_proxy.printer;
        this.pos = pos;
    }
    printWeb() {
        try {
            return super.printWeb(...arguments);
        } catch {
            this.popup.add(ErrorPopup, {
                title: _t("Printing is not supported on some browsers"),
                body: _t("It is possible to print your tickets by making use of an IoT System."),
            });
            return false;
        }
    }
    async printHtml() {
        this.setPrinter(this.hardware_proxy.printer);
        try {
            return await super.printHtml(...arguments);
        } catch (error) {
            return this.printHtmlAlternative(error, ...arguments);
        }
    }
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
}

registry.category("services").add("printer", posPrinterService);
