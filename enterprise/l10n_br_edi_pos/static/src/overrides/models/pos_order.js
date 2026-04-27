import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { qrCodeSrc } from "@point_of_sale/utils";

patch(PosOrder.prototype, {
    l10n_br_edi_get_nr_unique_items() {
        // As specified by DANFE NFC-e (Documento Auxiliar da Nota Fiscal Eletrônica):
        // The total count of distinct items (products or services) listed in the NFC-e. This refers to
        // the number of unique items, not the sum of their quantities.
        const unique_products = new Set(this.get_orderlines().map((line) => line.product_id));
        return unique_products.size;
    },

    format_access_key(key) {
        // Split into groups of 4, separated by a space:
        // 41250149233848000150550010000008271543438478 ->
        // 4125 0149 2338 4800 0150 5500 1000 0008 2715 4343 8478
        if (!key) {
            return "";
        }
        return key.match(/.{4}/g)?.join(" ") || "";
    },

    // @override
    set_to_invoice(to_invoice) {
        if (this.company.account_fiscal_country_id?.code === "BR") {
            super.set_to_invoice(false);
        } else {
            super.set_to_invoice(to_invoice);
        }
    },

    // @override
    export_for_printing(baseUrl, headerData) {
        const result = super.export_for_printing(...arguments);
        if (this.company.account_fiscal_country_id?.code !== "BR") {
            return result;
        }

        // Use the latest order data from the local db. "this" will contain outdated information in some cases, e.g.:
        // 1. Have failed EDI on a pos.order (e.g. no NCM code on a product),
        // 2. Select "Orders" from the dropdown in the top right,
        // 3. Select "Paid" orders in the dropdown,
        // 4. Select the failed order,
        // 5. Click Details,
        // 6. Fix the data to make EDI succeed (e.g. add NCM code on product),
        // 7. Click the "Retry EDI" button,
        // 8. When done, close the popup,
        // 9. Click "Print receipt"
        // TicketScreen's state.selectedOrder is still the old one, even though we re-read the pos.order in our orderDetailsProps override.
        const order = this.models["pos.order"].get(this.id);

        if (order.l10n_br_edi_avatax_data) {
            result.headerData.l10n_br_edi_avatax_data = order.l10n_br_edi_avatax_data;
            result.l10n_br_edi_avatax_data = order.l10n_br_edi_avatax_data;
            if (order.l10n_br_edi_avatax_data["header"]) {
                result.l10n_br_edi_qr = qrCodeSrc(
                    order.l10n_br_edi_avatax_data["header"]["goods"]["nfceQrCode"]
                );
            }
        }

        result.headerData.l10n_br_is_nfce = result.l10n_br_is_nfce = order.config.l10n_br_is_nfce;
        result.headerData.l10n_br_avalara_environment = result.l10n_br_avalara_environment =
            order.company.l10n_br_avalara_environment;
        result.l10n_br_access_key = this.format_access_key(order.l10n_br_access_key);
        result.l10n_br_edi_protocol_authorization_number =
            order.l10n_br_edi_protocol_authorization_number;
        result.l10n_br_edi_authorization_date = order.l10n_br_edi_authorization_date;
        result.l10n_br_edi_nr_unique_items = order.l10n_br_edi_get_nr_unique_items();
        result.l10n_br_edi_partner = order.get_partner();
        return result;
    },
});
