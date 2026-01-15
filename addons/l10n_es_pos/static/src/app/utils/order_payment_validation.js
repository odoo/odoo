import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(OrderPaymentValidation.prototype, {
    shouldDownloadInvoice() {
        return this.pos.config.is_spanish
            ? !this.order.is_l10n_es_simplified_invoice
            : super.shouldDownloadInvoice();
    },
    async beforePostPushOrderResolve(order, order_server_ids) {
        if (this.pos.config.is_spanish) {
            const invoiceName = await this.pos.data.call("pos.order", "get_invoice_name", [
                order_server_ids,
            ]);
            order.invoice_name = invoiceName;
        }
        return super.beforePostPushOrderResolve(...arguments);
    },
    async askBeforeValidation() {
        if (this.pos.config.is_spanish && !this.skipAutomaticInvoicing()) {
            this.order.is_l10n_es_simplified_invoice =
                this.order.canBeSimplifiedInvoiced() && !this.order.to_invoice;
            if (!this.order.is_l10n_es_simplified_invoice && !this.order.to_invoice) {
                this.pos.env.services.dialog.add(AlertDialog, {
                    title: _t("Error"),
                    body: _t(
                        "Order amount is too large for a simplified invoice, use an invoice instead."
                    ),
                });
                return false;
            }
            if (this.order.is_l10n_es_simplified_invoice) {
                this.order.to_invoice = Boolean(
                    this.pos.config.raw.l10n_es_simplified_invoice_journal_id
                );
                if ((await this._askForCustomerIfRequired()) === false) {
                    return false;
                }
                if (!this.order.partner_id && this.order.to_invoice) {
                    const setPricelist =
                        this.pos.config.pricelist_id?.id != this.order.pricelist_id?.id
                            ? this.order.pricelist_id
                            : false;
                    const setFiscalPosition =
                        this.pos.config.default_fiscal_position_id?.id !=
                        this.order.fiscal_position_id?.id
                            ? this.order.fiscal_position_id?.id
                            : false;
                    this.order.setPartner(this.pos.config.simplified_partner_id);
                    if (setPricelist) {
                        this.order.setPricelist(setPricelist);
                    }
                    if (setFiscalPosition !== false) {
                        this.order.update({ fiscal_position_id: setFiscalPosition });
                    }
                }
            }
        }
        return await super.askBeforeValidation();
    },

    skipAutomaticInvoicing() {
        if (
            this.pos.config.is_spanish &&
            this.order.is_settling_account &&
            this.order.lines.length === 0 &&
            !this.order.to_invoice
        ) {
            return true;
        }
        return false;
    },
});
