/** @odoo-module */
import { _t } from "@web/core/l10n/translation";
import {patch} from "@web/core/utils/patch";
import {ErrorPopup} from "@point_of_sale/app/errors/popups/error_popup";
import {PaymentScreen} from "@point_of_sale/app/screens/payment_screen/payment_screen";

patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        if (this.pos.config.is_spanish) {
            const order = this.currentOrder;
            order.is_l10n_es_simplified_invoice = order.canBeSimplifiedInvoiced() && !order.to_invoice;
            if (!order.is_l10n_es_simplified_invoice && !order.to_invoice) {
                this.popup.add(ErrorPopup, {
                    title: _t("Error"),
                    body: _t("Order amount is too large for a simplified invoice, use an invoice instead."),
                });
                return false;
            }
            if (order.is_l10n_es_simplified_invoice) {
                order.to_invoice = Boolean(this.pos.config.l10n_es_simplified_invoice_journal_id)
                order.partner = this.pos.db.partner_by_id[this.pos.config.simplified_partner_id[0]];
            }
        }
        return await super.validateOrder(...arguments);
    },
    shouldDownloadInvoice() {
        return this.pos.config.is_spanish
            ? !this.pos.selectedOrder.is_l10n_es_simplified_invoice
            : super.shouldDownloadInvoice();
    },
    async _postPushOrderResolve(order, order_server_ids) {
        if (this.pos.config.is_spanish) {
            const savedOrder = await this.orm.searchRead(
                "pos.order",
                [["id", "in", order_server_ids]],
                ["account_move"]
            );
            order.invoice_name = savedOrder[0].account_move[1];
        }
        return super._postPushOrderResolve(...arguments);
    },
});
