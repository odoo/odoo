import { EcpayInfoPopup } from "@l10n_tw_edi_ecpay_pos/js/ecpay_info_popup";
import { InvoiceButton } from "@point_of_sale/app/screens/ticket_screen/invoice_button/invoice_button";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { patch } from "@web/core/utils/patch";

patch(InvoiceButton.prototype, {
    async onWillInvoiceOrder(order, newPartner) {
        if (
            this.pos.company.country_id?.code === "TW" &&
            !order.is_to_invoice() &&
            !order.get_orderlines().some((line) => line.refunded_orderline_id) &&
            this.pos.config.is_ecpay_enabled
        ) {
            const payload = await makeAwaitable(this.dialog, EcpayInfoPopup, { order, newPartner });
            if (payload) {
                order.set_invoice_info(
                    "printFlag" in payload.data ? payload.data.printFlag : false,
                    "loveCode" in payload.data ? payload.data.loveCode : false,
                    "carrierType" in payload.data && payload.data.carrierType !== "0"
                        ? payload.data.carrierType
                        : false,
                    "carrierNumber" in payload.data ? payload.data.carrierNumber : false,
                    payload.data.invoiceType
                );
                await this.pos.data.ormWrite("pos.order", [order.id], {
                    l10n_tw_edi_is_print: order.l10n_tw_edi_is_print,
                    l10n_tw_edi_love_code: order.l10n_tw_edi_love_code,
                    l10n_tw_edi_carrier_type: order.l10n_tw_edi_carrier_type,
                    l10n_tw_edi_carrier_number: order.l10n_tw_edi_carrier_number,
                    l10n_tw_edi_invoice_type: order.l10n_tw_edi_invoice_type,
                });
            }
            return Boolean(payload);
        }
        return await super.onWillInvoiceOrder(...arguments);
    },
});
