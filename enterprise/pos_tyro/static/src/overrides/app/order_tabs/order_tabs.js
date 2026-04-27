import { OrderTabs } from "@point_of_sale/app/components/order_tabs/order_tabs";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(OrderTabs.prototype, {
    newFloatingOrder() {
        if (this.pos.get_order()?.tyro_payment_in_progress()) {
            this.dialog.add(AlertDialog, {
                title: _t("Payment in progress"),
                body: _t("Please complete or cancel the payment before navigatating away."),
            });
        } else {
            return super.newFloatingOrder(...arguments);
        }
    },
});
