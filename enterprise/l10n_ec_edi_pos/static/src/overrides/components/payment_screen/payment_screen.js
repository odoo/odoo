/** @odoo-module */

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(PaymentScreen.prototype, {
    async _isOrderValid(isForceValidate) {
        if (this.pos.isEcuadorianCompany()) {
            if (
                this.currentOrder._isRefundOrder() &&
                this.currentOrder.get_partner().id === this.pos.session._final_consumer_id
            ) {
                this.dialog.add(AlertDialog, {
                    title: _t("Refund not possible"),
                    body: _t("You cannot refund orders for Consumidor Final."),
                });
                return false;
            }
        }
        return super._isOrderValid(...arguments);
    },
    shouldDownloadInvoice() {
        return this.pos.isEcuadorianCompany() ? false : super.shouldDownloadInvoice();
    },
});
