import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        if (this.pos.config.is_spanish) {
            const order = this.currentOrder;
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
                order.to_invoice = Boolean(
                    this.pos.config.raw.l10n_es_simplified_invoice_journal_id
                );
                if ((await this._askForCustomerIfRequired()) === false) {
                    return false;
                }
                if (!order.partner_id) {
                    order.set_partner(this.pos.config.simplified_partner_id);
                }
            }
        }
        return await super.validateOrder(...arguments);
    },
    shouldDownloadInvoice() {
        return this.pos.config.is_spanish
            ? !this.pos.get_order().is_l10n_es_simplified_invoice
            : super.shouldDownloadInvoice();
    },
    async _postPushOrderResolve(order, order_server_ids) {
        if (this.pos.config.is_spanish) {
            const invoiceName = await this.pos.data.call("pos.order", "get_invoice_name", [
                order_server_ids,
            ]);
            order.invoice_name = invoiceName;
        }
        return super._postPushOrderResolve(...arguments);
    },
});
