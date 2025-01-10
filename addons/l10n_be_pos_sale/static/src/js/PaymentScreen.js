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
                this.currentOrder.setToInvoice(true);
            }
        });
    },
    toggleIsToInvoice() {
        if (this.checkIsToInvoice()) {
            this.dialog.add(AlertDialog, {
                title: _t("This order needs to be invoiced"),
                body: _t(
                    "If you do not invoice imported orders containing intra-community taxes you will encounter issues in your accounting. Especially in the EC Sales List report"
                ),
            });
        } else {
            super.toggleIsToInvoice(...arguments);
        }
    },
    checkIsToInvoice() {
        const orderLines = this.currentOrder.getOrderlines();
        const has_origin_order = orderLines.some((line) => line.sale_order_origin_id);
        const has_intracom_taxes = orderLines.some((line) =>
            line.tax_ids?.some((tax) => this.pos.session._intracom_tax_ids?.includes(tax.id))
        );
        if (
            this.pos.company.country_id &&
            this.pos.company.country_id.code === "BE" &&
            has_origin_order &&
            has_intracom_taxes
        ) {
            return true;
        }
    },
});
