import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { _t } from "@web/core/l10n/translation";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { patch } from "@web/core/utils/patch";
const { DateTime } = luxon;

patch(PosStore.prototype, {
    async selectPartner() {
        const currentOrder = this.get_order();
        if (!currentOrder) {
            return false;
        }
        const currentPartner = currentOrder.get_partner();
        const payload = await makeAwaitable(this.dialog, PartnerList, {
            partner: currentPartner,
            getPayload: (newPartner) => currentOrder.set_partner(newPartner),
        });

        if (payload) {
            currentOrder.set_partner(payload);
        } else {
            currentOrder.set_partner(false);
        }

        const res = await super.selectPartner(...arguments);
        if (res && document.querySelector("#ecpay_info_screen")) {
            document.querySelector("#identifier").value = res.vat || "";
            document.querySelector("#l10n_tw_edi_customer_name").value = res.name || "";
            document.querySelector("#l10n_tw_edi_customer_email").value = res.email || "";
            document.querySelector("#l10n_tw_edi_customer_phone").value = res.phone || "";
            document.querySelector("#l10n_tw_edi_customer_address").value =
                res.contact_address || "";
        }
        return res;
    },
    async syncAllOrders(options = {}) {
        const result = await super.syncAllOrders(options);

        if (result && result.length) {
            const posOrder = this.get_order();
            const uniform_inovice = await this.data.call("pos.order", "get_uniform_invoice", [
                posOrder.id,
                posOrder.name,
            ]);
            if (uniform_inovice) {
                posOrder.invoice_month = uniform_inovice.invoice_month;
                posOrder.iis_number = uniform_inovice.iis_number;
                posOrder.iis_create_date = DateTime.fromSQL(uniform_inovice.iis_create_date, {
                    zone: "utc",
                })
                    .toLocal()
                    .toFormat("yyyy-MM-dd HH:mm:ss");
                posOrder.iis_random_number = uniform_inovice.iis_random_number;
                posOrder.iis_tax_amount = uniform_inovice.iis_tax_amount;
                posOrder.l10n_tw_edi_invoice_amount = uniform_inovice.l10n_tw_edi_invoice_amount;
                posOrder.iis_identifier = uniform_inovice.iis_identifier;
                posOrder.iis_carrier_type =
                    posOrder.l10n_tw_edi_carrier_type === "0"
                        ? ""
                        : uniform_inovice.iis_carrier_type;
                posOrder.iis_carrier_num = uniform_inovice.iis_carrier_num;
                posOrder.iis_category = uniform_inovice.iis_category;
                posOrder.l10n_tw_edi_ecpay_seller_identifier =
                    uniform_inovice.l10n_tw_edi_ecpay_seller_identifier;
                posOrder.pos_barcode = uniform_inovice.pos_barcode;
                posOrder.qrcode_left = uniform_inovice.qrcode_left;
                posOrder.qrcode_right = uniform_inovice.qrcode_right;
                posOrder.error = uniform_inovice.error;
            }
            if (posOrder.error && posOrder.is_invoiced) {
                await this.dialog.add(AlertDialog, {
                    title: _t("Error to create/refund Ecpay invoice"),
                    body:
                        uniform_inovice.error.replace(/<[^>]*>/g, "") +
                        _t("\n You can go to the invoice to create ecpay invoice"),
                });
            }
        }
        return result;
    },
});
