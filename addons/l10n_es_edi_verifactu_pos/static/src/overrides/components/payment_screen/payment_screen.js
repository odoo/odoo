/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        if (this.pos.config.is_spanish) {
            const order = this.currentOrder;
            order.l10n_es_edi_verifactu_required = this.pos.config.l10n_es_edi_verifactu_required;
        }
        return await super.validateOrder(...arguments);
    },
    async _postPushOrderResolve(order, order_server_ids) {
        if (this.pos.config.is_spanish && this.pos.config.l10n_es_edi_verifactu_required) {
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
