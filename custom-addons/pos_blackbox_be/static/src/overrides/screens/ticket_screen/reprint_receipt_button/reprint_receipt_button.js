/** @odoo-module */

import { ReprintReceiptButton } from "@point_of_sale/app/screens/ticket_screen/reprint_receipt_button/reprint_receipt_button";
import { patch } from "@web/core/utils/patch";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

patch(ReprintReceiptButton.prototype, {
    setup() {
        super.setup();
        this.popup = useService("popup");
        this.orm = useService("orm");
    },
    async click() {
        if (this.pos.useBlackBoxBe()) {
            await this.popup.add(ErrorPopup, {
                title: _t("Fiscal Data Module Restriction"),
                body: _t(
                    "You are not allowed to reprint a ticket when using the fiscal data module."
                ),
            });
            return;
        }
        await super.click();
    },
});
