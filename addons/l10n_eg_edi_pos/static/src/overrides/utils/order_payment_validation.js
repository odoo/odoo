import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { patch } from "@web/core/utils/patch";

patch(OrderPaymentValidation.prototype, {
    async isOrderValid(isForceValidate) {
        const result = await super.isOrderValid(...arguments);
        const company = this.pos.config.company_id;

        if (
            !result ||
            company.account_fiscal_country_id?.code !== "EG" ||
            !this.pos.config.l10n_eg_edi_pos_enable
        ) {
            return result;
        }

        if (this.order.amount_total >= (company.l10n_eg_invoicing_threshold || 0)) {
            const partner = this.order.partner_id;
            if (!partner || !partner.name || !partner.vat) {
                this.pos.dialog.add(AlertDialog, {
                    title: _t("ETA Validation Error"),
                    body: _t(
                        "As the Order Value is equal to or above %s EGP, " +
                            "depending on the nature of the buyer, please either select " +
                            'an Individual Egypt Customer and fill in the "Tax ID" with ' +
                            "their National ID, or an Individual non-Egypt Customer.",
                        (company.l10n_eg_invoicing_threshold || 0).toLocaleString()
                    ),
                });
                return false;
            }
        }

        return result;
    },
});
