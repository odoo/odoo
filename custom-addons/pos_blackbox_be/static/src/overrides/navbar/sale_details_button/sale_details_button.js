/** @odoo-module */

import { SaleDetailsButton } from "@point_of_sale/app/navbar/sale_details_button/sale_details_button";
import { patch } from "@web/core/utils/patch";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { _t } from "@web/core/l10n/translation";

patch(SaleDetailsButton.prototype, {
    async onClick() {
        if (this.pos.useBlackBoxBe()) {
            await this.popup.add(ErrorPopup, {
                title: _t("Fiscal Data Module Restriction"),
                body: _t("You are not allowed to print a sales report details when using the fiscal data module."),
            });
            return;
        }
        return super.onClick();
    }
});
