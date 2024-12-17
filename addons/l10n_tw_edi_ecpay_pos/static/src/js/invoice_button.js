import { ask, makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { EcpayInfoPopup } from "@l10n_tw_edi_ecpay_pos/js/ecpay_info_popup";
import { InvoiceButton } from "@point_of_sale/app/screens/ticket_screen/invoice_button/invoice_button";
import { _t } from "@web/core/l10n/translation";
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
        let isConfirm = await super.onWillInvoiceOrder(order, newPartner);
        if (
            this.pos.company.country_id?.code === "TW" &&
            this.pos.config.is_ecpay_enabled &&
            newPartner &&
            !order.is_to_invoice() &&
            !order.get_orderlines().some((line) => line.refunded_orderline_id) &&
            !order.l10n_tw_edi_is_b2b
        ) {
            let dismiss = false;
            const confirm = await ask(this.dialog, {
                title: _t("Ecpay Invoicing Confirmation"),
                body: _t("Store in Carrier or Donate?"),
                confirmLabel: _t("Yes"),
                cancelLabel: _t("No"),
                dismiss: () => {
                    dismiss = true;
                },
            });

            if (dismiss) {
                return false;
            }

            if (confirm) {
                const payload = await makeAwaitable(this.dialog, EcpayInfoPopup);
                if (payload) {
                    await this.writeToOrder(
                        order,
                        false,
                        "loveCode" in payload ? payload.loveCode : false,
                        "carrierType" in payload && payload.carrierType !== "0"
                            ? payload.carrierType
                            : false,
                        "carrierNumber" in payload ? payload.carrierNumber : false,
                        "carrierNumber2" in payload ? payload.carrierNumber2 : false
                    );
                }
                isConfirm &= Boolean(payload);
            } else {
                await this.writeToOrder(order, true, false, false, false, false);
            }
            isConfirm &= Boolean(confirm);
        }
        return isConfirm;
    },
});
