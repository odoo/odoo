/** @odoo-module */

import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(ReceiptScreen.prototype, {
    async printReceipt() {
        if (this.pos.useBlackBoxBe()) {
            this.env.services.popup.add(ErrorPopup, {
                title: _t("Fiscal data module error"),
                body: _t("You're not allowed to reprint a ticket when using the blackbox."),
            });
            return;
        }
        await super.printReceipt();
    },
});
