/** @odoo-module */

import { PosPrinterService } from "@point_of_sale/app/printer/pos_printer_service";
import { patch } from "@web/core/utils/patch";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { _t } from "@web/core/l10n/translation";

patch(PosPrinterService.prototype, {
    printWeb() {
        if (this.pos.useBlackBoxBe()) {
            this.popup.add(ErrorPopup, {
                title: _t("Fiscal data module error"),
                body: _t(
                    "You're not allowed to download a ticket when using the blackbox. Please connect a printer to print the ticket."
                ),
            });
            return false;
        }
        return super.printWeb(...arguments);
    },
    async printHtmlAlternative(error) {
        if (this.pos.useBlackBoxBe()) {
            this.popup.add(ErrorPopup, {
                title: _t("Fiscal data module error"),
                body: _t(
                    "You're not allowed to download a ticket when using the blackbox. Please connect a printer to print the ticket."
                ),
            });
            return false;
        }
        return await super.printHtmlAlternative(...arguments);
    },
});
