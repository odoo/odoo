/** @odoo-module **/

import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(PaymentScreen.prototype, {
    async toggleIsToInvoice() {
        const orderLines = this.currentOrder.get_orderlines();
        const has_origin_order = orderLines.some(line => line.sale_order_origin_id);
        const has_intracom_taxes = orderLines.some(line=>line.tax_ids?.some(tax=>this.pos.intracom_tax_ids?.includes(tax)));
        if(this.currentOrder.is_to_invoice() && this.pos.company.country?.code === "BE" && has_origin_order && has_intracom_taxes){
            this.popup.add(ErrorPopup, {
                title: _t('This order needs to be invoiced'),
                body: _t('If you do not invoice imported orders containing intra-community taxes you will encounter issues in your accounting. Especially in the EC Sales List report'),
            });
        }
        else{
            super.toggleIsToInvoice(...arguments);
        }
    }
});
