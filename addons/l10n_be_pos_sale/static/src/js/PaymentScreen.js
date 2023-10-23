/** @odoo-module **/

import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(PaymentScreen.prototype, {
    toggleIsToInvoice() {
        const has_origin_order = this.currentOrder.get_orderlines().some(line => line.sale_order_origin_id);
        if(this.currentOrder.is_to_invoice() && this.pos.company.country_id && this.pos.company.country_id.code === "BE" && has_origin_order){
            this.dialog.add(AlertDialog, {
                title: _t('This order needs to be invoiced'),
                body: _t('If you do not invoice imported orders you will encounter issues in your accounting. Especially in the EC Sale List report'),
            });
        }
        else{
            super.toggleIsToInvoice(...arguments);
        }
    }
});
