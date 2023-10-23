/** @odoo-module **/

import { ErrorPopup } from "@point_of_sale/js/Popups/ErrorPopup";
import { PaymentScreen } from "@point_of_sale/js/Screens/PaymentScreen/PaymentScreen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, "l10n_be_pos_sale.PaymentScreen", {
    toggleIsToInvoice() {
        const _super = this._super;
        const has_origin_order = this.currentOrder.get_orderlines().some(line => line.sale_order_origin_id);
        if(this.currentOrder.is_to_invoice() && this.pos.globalState.company.country && this.pos.globalState.company.country.code === "BE" && has_origin_order){
            this.popup.add(ErrorPopup, {
                title: this.env._t('This order needs to be invoiced'),
                body: this.env._t('If you do not invoice imported orders you will encounter issues in your accounting. Especially in the EC Sale List report'),
            });
        }
        else{
            _super();
        }
    }
});
