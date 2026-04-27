import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";
import { pick } from "@web/core/utils/objects";
import { formatDateTime } from "@web/core/l10n/dates";
import { parseUTCString } from "@point_of_sale/utils";

patch(PosStore.prototype, {
    // @Override
    async processServerData() {
        await super.processServerData();

        if (this.isChileanCompany()) {
            this["l10n_latam.identification.type"] =
                this.models["l10n_latam.identification.type"].getFirst();
        }
    },
    isChileanCompany() {
        return this.company.country_id?.code == "CL";
    },
    doNotAllowRefundAndSales() {
        return this.isChileanCompany() || super.doNotAllowRefundAndSales(...arguments);
    },
    getSyncAllOrdersContext(orders, options = {}) {
        let context = super.getSyncAllOrdersContext(...arguments);
        if (this.isChileanCompany() && orders) {
            // FIXME in master: when processing multiple orders, and at least one is an invoice of type Factura,
            //  then we will generate the pdf for all invoices linked to the orders,
            //  since the context is applicable for the whole RPC requests `create_from_ui` on all orders.
            const noOrderRequiresInvoicePrinting = orders.every(
                (order) => order.to_invoice && order.invoice_type === "boleta"
            );
            if (noOrderRequiresInvoicePrinting) {
                context = { ...context, generate_pdf: false };
            }
        }
        return context;
    },
    createNewOrder() {
        const order = super.createNewOrder(...arguments);
        if (!order.partner_id && this.isChileanCompany()) {
            order.update({ partner_id: this.session._consumidor_final_anonimo_id });
        }
        return order;
    },
    getReceiptHeaderData(order) {
        const result = super.getReceiptHeaderData(...arguments);
        if (!this.isChileanCompany() || !order) {
            return result;
        }
        result.company.cl_vat = this.company.vat;
        result.l10n_cl_sii_regional_office =
            this.session._l10n_cl_sii_regional_office_selection[
                order.company_id.l10n_cl_sii_regional_office
            ];
        result.l10n_latam_document_type = order.account_move?.l10n_latam_document_type_id?.name;
        result.l10n_latam_document_number = order.account_move?.l10n_latam_document_number;
        result.date = formatDateTime(parseUTCString(order.date_order));
        result.partner = order.isFactura()
            ? pick(
                  order.get_partner(),
                  "name",
                  "vat",
                  "street",
                  "street2",
                  "city",
                  "l10n_cl_activity_description",
                  "phone"
              )
            : false;

        return result;
    },
});
