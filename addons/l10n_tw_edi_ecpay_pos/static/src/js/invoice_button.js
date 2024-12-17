/* eslint-disable max-depth */
import { EcpayConfirmPopup } from "@l10n_tw_edi_ecpay_pos/js/ecpay_confirm_popup";
import { EcpayInfoPopup } from "@l10n_tw_edi_ecpay_pos/js/ecpay_info_popup";
import { InvoiceButton } from "@point_of_sale/app/screens/ticket_screen/invoice_button/invoice_button";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { patch } from "@web/core/utils/patch";

patch(InvoiceButton.prototype, {
    async writeToOrder(
        order,
        l10n_tw_edi_is_print,
        l10n_tw_edi_love_code,
        l10n_tw_edi_carrier_type,
        l10n_tw_edi_carrier_number,
        l10n_tw_edi_carrier_number_2
    ) {
        order.l10n_tw_edi_is_print = l10n_tw_edi_is_print;
        order.l10n_tw_edi_love_code = l10n_tw_edi_love_code;
        order.l10n_tw_edi_carrier_type = l10n_tw_edi_carrier_type;
        order.l10n_tw_edi_carrier_number = l10n_tw_edi_carrier_number;
        order.l10n_tw_edi_carrier_number_2 = l10n_tw_edi_carrier_number_2;
        await this.pos.data.ormWrite("pos.order", [order.id], {
            l10n_tw_edi_is_print: order.l10n_tw_edi_is_print,
            l10n_tw_edi_love_code: order.l10n_tw_edi_love_code,
            l10n_tw_edi_carrier_type: order.l10n_tw_edi_carrier_type,
            l10n_tw_edi_carrier_number: order.l10n_tw_edi_carrier_number,
            l10n_tw_edi_carrier_number_2: order.l10n_tw_edi_carrier_number_2,
        });
    },

    async onWillInvoiceOrder(order, newPartner) {
        if (
            this.pos.company.country_id?.code === "TW" &&
            this.pos.config.is_ecpay_enabled &&
            newPartner &&
            !order.is_to_invoice() &&
            !order.get_orderlines().some((line) => line.refunded_orderline_id) &&
            !order.l10n_tw_edi_is_b2b
        ) {
            const confirm = await makeAwaitable(this.dialog, EcpayConfirmPopup, {
                order,
                newPartner,
            });

            if (confirm) {
                if (confirm.confirm === 1) {
                    const payload = await makeAwaitable(this.dialog, EcpayInfoPopup, {
                        order,
                        newPartner,
                    });
                    if (payload) {
                        await this.writeToOrder(
                            order,
                            false,
                            "loveCode" in payload.data ? payload.data.loveCode : false,
                            "carrierType" in payload.data && payload.data.carrierType !== "0"
                                ? payload.data.carrierType
                                : false,
                            "carrierNumber" in payload.data ? payload.data.carrierNumber : false,
                            "carrierNumber2" in payload.data ? payload.data.carrierNumber2 : false
                        );
                    } else {
                        await this.writeToOrder(order, false, false, false, false, false);
                    }
                    return Boolean(payload);
                }
                await this.writeToOrder(order, true, false, false, false, false);
            } else {
                await this.writeToOrder(order, false, false, false, false, false);
            }
            return Boolean(confirm);
        }
        return await super.onWillInvoiceOrder(...arguments);
    },
});
