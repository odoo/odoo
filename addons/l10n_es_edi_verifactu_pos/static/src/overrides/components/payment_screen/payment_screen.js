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
            const canBeSimplified = this.env.utils.roundCurrency(order.get_total_with_tax()) <= 400;
            if (!canBeSimplified && !order.to_invoice) {
                this.popup.add(ErrorPopup, {
                    title: _t("Error"),
                    body: _t("The order needs to be invoiced since its total amount is above 400€."),
                });
                return false;
            }
        }
        return await super.validateOrder(...arguments);
    },

    async _postPushOrderResolve(order, order_server_ids) {
        if (this.pos.config.l10n_es_edi_verifactu_required) {
            const [orderRead] = await this.orm.read(
                'pos.order',
                order_server_ids,
                ['l10n_es_edi_verifactu_qr_code'],
            );
            order.l10n_es_edi_verifactu_qr_code = orderRead.l10n_es_edi_verifactu_qr_code;
        }
        return super._postPushOrderResolve(...arguments);
    },
});
