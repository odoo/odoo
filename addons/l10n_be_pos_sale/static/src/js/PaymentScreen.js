/** @odoo-module **/

import PaymentScreen from 'point_of_sale.PaymentScreen';
import Registries from 'point_of_sale.Registries';

export const PoSSaleBePaymentScreen = (PaymentScreen) =>
    class extends PaymentScreen {
        toggleIsToInvoice() {
            const orderLines = this.currentOrder.get_orderlines();
            const has_origin_order = orderLines.some((line) => line.sale_order_origin_id);
            const has_intracom_taxes = orderLines.some((line) =>
                line.tax_ids && this.env.pos.intracom_tax_ids && line.tax_ids.some((tax) => this.env.pos.intracom_tax_ids.includes(tax))
            );
            if (
                this.currentOrder.is_to_invoice() &&
                this.env.pos.company.country.code === "BE" &&
                has_origin_order &&
                has_intracom_taxes
            ) {
                this.showPopup('ErrorPopup', {
                    title: this.env._t('This order needs to be invoiced'),
                    body: this.env._t('If you do not invoice imported orders containing intra-community taxes you will encounter issues in your accounting. Especially in the EC Sales List report'),
                });
            }
            else{
                super.toggleIsToInvoice();
            }
        }
    };

Registries.Component.extend(PaymentScreen, PoSSaleBePaymentScreen);
