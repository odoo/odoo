import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { PosAlertDialog } from "@point_of_sale/app/components/alert_dialog/pos_alert_dialog";

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
            this.pos.dialog.add(PosAlertDialog, {
                title: _t("Missing Field"),
                body: _t("An Identification Number Is Required"),
            });
            return false;
        }
        return res;
    },
});
