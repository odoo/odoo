import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        if (this.pos.useBlackBoxBe() && !this.pos.checkIfUserClocked()) {
            this.dialog.add(AlertDialog, {
                title: _t("POS error"),
                body: _t("User must be clocked in."),
            });
            return;
        }
        await super.validateOrder(isForceValidate);
    },
});
