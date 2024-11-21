/** @odoo-module **/

import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { onMounted } from "@odoo/owl";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        onMounted(() => {
            if (this.checkIsToInvoice()) {
                this.currentOrder.set_to_invoice(true);
            }
        });
    },
    toggleIsToInvoice() {
        if (this.checkIsToInvoice()) {
            this.dialog.add(AlertDialog, {
                title: _t("This order needs to be invoiced"),
                body: _t(
                    "If you do not invoice imported orders you will encounter issues in your accounting. Especially in the EC Sale List report"
                ),
            });
        } else {
            super.toggleIsToInvoice(...arguments);
        }
    },
    checkIsToInvoice() {
        const has_origin_order = this.currentOrder
            .get_orderlines()
            .some((line) => line.sale_order_origin_id);
        if (
            this.pos.company.country_id &&
            this.pos.company.country_id.code === "BE" &&
            has_origin_order
        ) {
            return true;
        }
    },
});
