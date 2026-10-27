/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    async _isOrderValid(isForceValidate) {
        const res = await super._isOrderValid(...arguments);
        if (!this.pos.isPeruvianCompany() && res) {
            return res;
        }
        if (!res) {
            return false;
        }
        const currentPartner = this.currentOrder.get_partner();
        if (currentPartner && !currentPartner.vat) {
            this.popup.add(ErrorPopup, {
                title: _t("Missing Field"),
                body: _t("A Identification Number Is Required"),
            });
            this.selectPartner(true, ["vat"]);
            return false;
        }
        return res;
    },
});
