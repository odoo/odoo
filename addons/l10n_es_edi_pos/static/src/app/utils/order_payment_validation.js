import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(OrderPaymentValidation.prototype, {
    async askBeforeValidation() {
        if (this.order.l10nEsPosFiscalMode && this.order.isToInvoice()) {
            // An invoice must identify its recipient, unlike a simplified invoice.
            if (!(await this.l10nEsPosEnsureIdentifiedPartner())) {
                return false;
            }
        }
        // Block the payment before anything is sent to the server: the server check
        // (`_l10n_es_pos_check_simplified_invoice_limit`) remains as the safeguard for
        // orders reaching it by other means.
        if (
            this.order.l10nEsPosFiscalMode &&
            !this.order.isToInvoice() &&
            !this.order.l10nEsPosCanBeSimplifiedInvoice()
        ) {
            this.pos.env.services.dialog.add(AlertDialog, {
                title: _t("Invoice required"),
                body: _t(
                    "The order amount is above the simplified invoice limit. Select a customer and request an invoice to validate it."
                ),
            });
            return false;
        }
        return await super.askBeforeValidation(...arguments);
    },

    /**
     * Make sure the customer of an order to invoice can be identified on the invoice.
     * The generic partner of the simplified invoices is replaced by a real customer, and a
     * customer without Tax ID is opened to complete it.
     *
     * @returns {Promise<boolean>} whether the validation can go on
     */
    async l10nEsPosEnsureIdentifiedPartner() {
        let partner = this.order.getPartner();
        if (!partner || partner.id === this.pos.config._l10n_es_pos_simplified_partner_id) {
            partner = await this.pos.selectPartner(this.order);
            if (!partner) {
                return false;
            }
        }
        if (this.l10nEsPosIsPartnerIdentified(partner)) {
            return true;
        }
        this.pos.notification.add(_t("The customer needs a Tax ID to be invoiced."), {
            type: "warning",
        });
        await this.pos.editPartner(partner);
        return this.l10nEsPosIsPartnerIdentified(this.order.getPartner());
    },

    l10nEsPosIsPartnerIdentified(partner) {
        return Boolean(partner?.vat);
    },
});
