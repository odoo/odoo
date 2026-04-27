import { InvoiceButton } from "@point_of_sale/app/screens/ticket_screen/invoice_button/invoice_button";
import { AddInfoPopup } from "@l10n_mx_edi_pos/app/add_info_popup/add_info_popup";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { patch } from "@web/core/utils/patch";

patch(InvoiceButton.prototype, {
    async onWillInvoiceOrder(order, newPartner) {
        if (this.pos.company.country_id?.code !== "MX") {
            return true;
        }
        const payload = await makeAwaitable(this.dialog, AddInfoPopup, { order, newPartner });
        if (payload) {
            order.l10n_mx_edi_cfdi_to_public =
                payload.l10n_mx_edi_cfdi_to_public === true ||
                payload.l10n_mx_edi_cfdi_to_public === "1";
            order.l10n_mx_edi_usage = payload.l10n_mx_edi_usage;
            await this.pos.data.ormWrite("pos.order", [order.id], {
                l10n_mx_edi_cfdi_to_public: order.l10n_mx_edi_cfdi_to_public,
                l10n_mx_edi_usage: order.l10n_mx_edi_usage,
            });
        }
        return Boolean(payload);
    },
});
