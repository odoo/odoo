/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        if (!this.pos.config.is_spanish) {
            return await super.validateOrder(...arguments);
        }
        const order = this.currentOrder;
        this.currentOrder.to_invoice = true;
        const simplified_partner =
            this.pos.db.partner_by_id[this.pos.config.simplified_partner_id[0]];
        if (order.canBeSimplifiedInvoiced()) {
            order.is_l10n_es_simplified_invoice ??= true;
        } else {
            order.is_l10n_es_simplified_invoice = false;
        }
        order.partner ||= simplified_partner;
        if (!order.is_l10n_es_simplified_invoice && order.partner.id === simplified_partner.id) {
            order.partner = null;
        }
        return await super.validateOrder(...arguments);
    },
    toggleIsToInvoice() {
        super.toggleIsToInvoice(...arguments);
        if (
            this.currentOrder.to_invoice &&
            this.pos.config.is_spanish &&
            this.currentOrder.canBeSimplifiedInvoiced()
        ) {
            this.currentOrder.is_l10n_es_simplified_invoice = false;
        }
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
