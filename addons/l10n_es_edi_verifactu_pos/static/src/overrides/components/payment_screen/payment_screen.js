/** @odoo-module */
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import {ErrorPopup} from "@point_of_sale/app/errors/popups/error_popup";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        if (this.pos.config.l10n_es_edi_verifactu_required) {
            const order = this.currentOrder;
            order.l10n_es_edi_verifactu_required = true;
            const simplifiedInvoiceLimit = this.pos.config.l10n_es_edi_verifactu_simplified_invoice_limit ?? 400;
            const canBeSimplified = this.env.utils.roundCurrency(order.get_total_with_tax()) <= simplifiedInvoiceLimit;
            if (!canBeSimplified && !order.to_invoice) {
                this.popup.add(ErrorPopup, {
                    title: _t("Error"),
                    body: _t("Order amount is too large for a simplified invoice, use an invoice instead."),
                });
                return false;
            }
        }
        return await super.validateOrder(...arguments);
    },

    async _postPushOrderResolve(order, order_server_ids) {
        if (this.pos.config.l10n_es_edi_verifactu_required) {
            const [res] = await this.pos.selectedOrder.fetch_l10n_es_edi_verifactu_qr_code(order_server_ids);
            order.l10n_es_edi_verifactu_qr_code = res.l10n_es_edi_verifactu_qr_code;
        }
        return super._postPushOrderResolve(...arguments);
    },
});
