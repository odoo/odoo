import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(PosStore.prototype, {
    _getCreateOrderContext(orders, options) {
        let context = super._getCreateOrderContext(...arguments);
        if (this.config.is_spanish) {
            const noOrderRequiresInvoicePrinting = orders.every(
                (order) => !order.to_invoice && order.data.is_l10n_es_simplified_invoice
            );
            if (noOrderRequiresInvoicePrinting) {
                context = { ...context, generate_pdf: false };
            }
        }
        return context;
    },

    async askBeforeValidation() {
        if (this.config.is_spanish && !this.skipAutomaticInvoicing()) {
            const order = this.getOrder();
            order.is_l10n_es_simplified_invoice =
                order.canBeSimplifiedInvoiced() && !order.to_invoice;
            if (!order.is_l10n_es_simplified_invoice && !order.to_invoice) {
                this.env.services.dialog.add(AlertDialog, {
                    title: _t("Error"),
                    body: _t(
                        "Order amount is too large for a simplified invoice, use an invoice instead."
                    ),
                });
                return false;
            }
            if (order.is_l10n_es_simplified_invoice) {
                order.to_invoice = Boolean(this.config.raw.l10n_es_simplified_invoice_journal_id);
                if ((await this._askForCustomerIfRequired()) === false) {
                    return false;
                }
                if (!order.partner_id && order.to_invoice) {
                    const setPricelist =
                        this.config.pricelist_id?.id != order.pricelist_id?.id
                            ? order.pricelist_id
                            : false;
                    order.setPartner(this.config.simplified_partner_id);
                    if (setPricelist) {
                        order.setPricelist(setPricelist);
                    }
                }
            }
        }
        return await super.askBeforeValidation();
    },
    skipAutomaticInvoicing() {
        const order = this.getOrder();
        if (
            this.config.is_spanish &&
            order.is_settling_account &&
            order.lines.length === 0 &&
            !order.to_invoice
        ) {
            return true;
        }
        return false;
    },
});
