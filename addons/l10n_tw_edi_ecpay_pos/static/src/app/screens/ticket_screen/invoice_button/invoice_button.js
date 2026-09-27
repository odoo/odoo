import { InvoiceButton } from "@point_of_sale/app/screens/ticket_screen/invoice_button/invoice_button";
import { patch } from "@web/core/utils/patch";

patch(InvoiceButton.prototype, {
    // @override
    async onWillInvoiceOrder(order, newPartner) {
        const isConfirm = await super.onWillInvoiceOrder(order, newPartner);

        if (isConfirm) {
            const ecpaySuccess = await order.askAndSetEcpayInvoiceInfo(this.dialog, {
                partner: newPartner,
            });

            if (!ecpaySuccess) {
                return false;
            }

            if (!order.l10n_tw_edi_is_print) {
                await this.pos.data.ormWrite("pos.order", [order.id], {
                    l10n_tw_edi_love_code: order.l10n_tw_edi_love_code,
                    l10n_tw_edi_carrier_type: order.l10n_tw_edi_carrier_type,
                    l10n_tw_edi_carrier_number: order.l10n_tw_edi_carrier_number,
                    l10n_tw_edi_carrier_number_2: order.l10n_tw_edi_carrier_number_2,
                });
            } else {
                await this.pos.data.ormWrite("pos.order", [order.id], {
                    l10n_tw_edi_is_print: true,
                });
            }
        }
        return isConfirm;
    },
});
