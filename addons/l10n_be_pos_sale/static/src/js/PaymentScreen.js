/** @odoo-module **/

import PaymentScreen from 'point_of_sale.PaymentScreen';
import Registries from 'point_of_sale.Registries';

export const PoSSaleBePaymentScreen = (PaymentScreen) =>
    class extends PaymentScreen {
        toggleIsToInvoice() {
            const has_origin_order = this.currentOrder.get_orderlines().some(line => line.sale_order_origin_id);
            if(this.currentOrder.is_to_invoice() && this.env.pos.company.country && this.env.pos.company.country.code === "BE" && has_origin_order){
                this.showPopup('ErrorPopup', {
                    title: this.env._t('This order needs to be invoiced'),
                    body: this.env._t('If you do not invoice imported orders you will encounter issues in your accounting. Especially in the EC Sale List report'),
                });
            }
            else{
                super.toggleIsToInvoice();
            }
        }
    };

Registries.Component.extend(PaymentScreen, PoSSaleBePaymentScreen);
