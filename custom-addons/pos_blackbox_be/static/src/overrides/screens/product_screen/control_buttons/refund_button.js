/** @odoo-module */

import { RefundButton } from "@point_of_sale/app/screens/product_screen/control_buttons/refund_button/refund_button";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { patch } from "@web/core/utils/patch";

patch(RefundButton.prototype, {
    click() {
        if (this.pos.useBlackBoxBe() && !this.pos.checkIfUserClocked()) {
            this.pos.env.services.popup.add(ErrorPopup, {
                'title': this._t("POS error"),
                'body':  this._t("User must be clocked in."),
            });
            return;
        }
        super.click();
    },
});
