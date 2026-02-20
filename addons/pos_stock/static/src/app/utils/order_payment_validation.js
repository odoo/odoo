import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { ask } from "@point_of_sale/app/utils/make_awaitable_dialog";
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";

patch(OrderPaymentValidation.prototype, {
    async isOrderValid(isForceValidate) {
        const isValid = super.isOrderValid(isForceValidate);
        if (this.order.shipping_date && !this.order.getPartner()) {
            const confirmed = await ask(this.pos.dialog, {
                title: _t("Please select the Customer"),
                body: _t("Select a customer with a valid address."),
                confirmLabel: _t("Customer"),
            });
            if (confirmed) {
                const partner = await this.pos.selectPartner();
                if (!partner) {
                    return false;
                }
            } else {
                return false;
            }
        }
        const partner = this.order.getPartner();
        if (
            this.order.shipping_date &&
            !(partner.name && partner.street && partner.city && partner.country_id)
        ) {
            this.pos.dialog.add(AlertDialog, {
                title: _t("Incorrect address for shipping"),
                body: _t("The selected customer needs an address."),
            });
            return false;
        }
        return isValid;
    },
});
