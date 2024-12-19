import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
const { DateTime } = luxon;
import {
    makeAwaitable,
} from "@point_of_sale/app/store/make_awaitable_dialog";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";

patch(PosStore.prototype, {
    async selectPartner() {
        const currentOrder = this.get_order();
        if (!currentOrder) {
            return false;
        }
        const currentPartner = currentOrder.get_partner();
        if (currentPartner && currentOrder.getHasRefundLines()) {
            this.dialog.add(AlertDialog, {
                title: _t("Can't change customer"),
                body: _t(
                    "This order already has refund lines for %s. We can't change the customer associated to it. Create a new order for the new customer.",
                    currentPartner.name
                ),
            });
            return currentPartner;
        }
        const payload = await makeAwaitable(this.dialog, PartnerList, {
            partner: currentPartner,
            getPayload: (newPartner) => currentOrder.set_partner(newPartner),
        });

        if (payload) {
            currentOrder.set_partner(payload);
            if (document.querySelector("#ecpay_info_screen")) {
                document.querySelector("#l10n_tw_edi_customer_name").value = payload.name || ''
                document.querySelector("#l10n_tw_edi_customer_email").value = payload.email || ''
                document.querySelector("#l10n_tw_edi_customer_phone").value = payload.phone || ''
                document.querySelector("#l10n_tw_edi_customer_address").value = payload.contact_address || ''
            }
        } else {
            currentOrder.set_partner(false);
        }

        return currentPartner;
    },

    _formatDateTime (datetimeValue) {
        return DateTime.fromSQL(datetimeValue, { zone: "utc" }).toLocal().toFormat('yyyy-MM-dd HH:mm:ss');
    },

    async syncAllOrders(options = {}) {
        const result = await super.syncAllOrders(options);

        if (result && result.length) {
            const posOrder = this.get_order();
            const uniform_inovice = await this.data.call(
                "pos.order",
                "get_uniform_invoice",
                [posOrder.id, posOrder.name],
            );
            if (uniform_inovice) {
                posOrder.invoice_month = uniform_inovice.invoice_month;
                posOrder.IIS_Number = uniform_inovice.IIS_Number;
                posOrder.IIS_Create_Date = this._formatDateTime(uniform_inovice.IIS_Create_Date);
                posOrder.IIS_Random_Number = uniform_inovice.IIS_Random_Number;
                posOrder.IIS_Tax_Amount = uniform_inovice.IIS_Tax_Amount;
                posOrder.l10n_tw_edi_invoice_amount = uniform_inovice.l10n_tw_edi_invoice_amount;
                posOrder.IIS_Identifier = uniform_inovice.IIS_Identifier;
                posOrder.IIS_Carrier_Type = posOrder.l10n_tw_edi_carrier_type === "0" ? "" : uniform_inovice.IIS_Carrier_Type
                posOrder.IIS_Carrier_Num = uniform_inovice.IIS_Carrier_Num;
                posOrder.IIS_Category = uniform_inovice.IIS_Category;
                posOrder.l10n_tw_edi_ecpay_seller_identifier = uniform_inovice.l10n_tw_edi_ecpay_seller_identifier;
                posOrder.PosBarCode = uniform_inovice.PosBarCode;
                posOrder.QRCode_Left = uniform_inovice.QRCode_Left;
                posOrder.QRCode_Right = uniform_inovice.QRCode_Right;
                posOrder.error = uniform_inovice.error;
            }
            if (posOrder.error && posOrder.is_invoiced) {
                await this.dialog.add(AlertDialog, {
                    title: _t("Error to create/refund Ecpay invoice"),
                    body: uniform_inovice.error.replace(/<[^>]*>/g, '') + _t("\n You can go to the invoice to create ecpay invoice"),
                });
            }
        }
        return result
    },
})
