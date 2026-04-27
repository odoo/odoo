import { SaleDetailsButton } from "@point_of_sale/app/navbar/sale_details_button/sale_details_button";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(SaleDetailsButton.prototype, {
    async onClick() {
        if (this.pos.useBlackBoxBe()) {
            await this.dialog.add(AlertDialog, {
                title: _t("Fiscal Data Module Restriction"),
                body: _t(
                    "You are not allowed to print a sales report details in the POS when using the fiscal data module."
                ),
            });
            return;
        }
        return await super.onClick();
    },
});
