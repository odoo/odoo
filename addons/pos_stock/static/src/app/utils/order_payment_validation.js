import { patch } from "@web/core/utils/patch";
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(OrderPaymentValidation.prototype, {
    async isOrderValid(isForceValidate) {
        const isOrderValid = await super.isOrderValid(isForceValidate);
        const partner = this.order.getPartner();
        if (
            isOrderValid &&
            this.order.shipping_date &&
            !(partner.name && partner.street && partner.city && partner.country_id)
        ) {
            this.pos.dialog.add(AlertDialog, {
                title: _t("Incorrect address for shipping"),
                body: _t("The selected customer needs an address."),
            });
            return false;
        }
        return isOrderValid;
    },

    shouldAskForPartner() {
        return (
            super.shouldAskForPartner() || (this.order.shipping_date && !this.order.getPartner())
        );
    },

    async finalizeValidation() {
        const res = await super.finalizeValidation();
        try {
            // Print stock reports if needed.
            if (this.order.picking_type_id?.has_stock_reports_to_print) {
                const reports = await this.pos.data.call(
                    "pos.order",
                    "get_stock_reports_to_print",
                    [this.order.id]
                );
                for (const report of reports) {
                    await this.pos.action.doAction(report);
                }
            }
        } catch (error) {
            return this.handleValidationError(error);
        }
        return res;
    },
});
