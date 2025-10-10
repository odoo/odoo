import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    onMounted() {
        super.onMounted();
        if (this.pos.isPeruvianCompany()) {
            this.currentOrder.set_to_invoice(true);
        }
    },
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
            this.pos.editPartner(currentPartner);
            this.dialog.add(AlertDialog, {
                title: _t("Missing Field"),
                body: _t("An Identification Number Is Required"),
            });
            return false;
        }
        return res;
    },
});
