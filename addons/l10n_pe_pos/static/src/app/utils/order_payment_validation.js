import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { AlertDialog } from "@web/ui/dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
patch(OrderPaymentValidation.prototype, {
    async isOrderValid(isForceValidate) {
        const res = await super.isOrderValid(...arguments);
        if (!this.pos.isPeruvianCompany() && res) {
            return res;
        }
        if (!res) {
            return false;
        }
        const currentPartner = this.order.getPartner();
        if (currentPartner && !currentPartner.vat) {
            this.pos.editPartner(currentPartner);
            this.pos.dialog.add(AlertDialog, {
                title: _t("Missing Field"),
                body: _t("An Identification Number Is Required"),
            });
            return false;
        }
        return res;
    },
});
