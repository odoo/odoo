/** @odoo-module */

import { InvoiceButton } from "@point_of_sale/app/screens/ticket_screen/invoice_button/invoice_button";
import { AddInfoPopup } from "@l10n_mx_edi_pos/app/add_info_popup/add_info_popup";
import { patch } from "@web/core/utils/patch";

patch(InvoiceButton.prototype, {
    async onWillInvoiceOrder(order){
        if (this.pos.company.country?.code !== 'MX') {
            return true;
        }
        const { confirmed, payload } = await this.popup.add(AddInfoPopup, { order });
        if (confirmed) {
            order.l10n_mx_edi_cfdi_to_public = (payload.l10n_mx_edi_cfdi_to_public === true || payload.l10n_mx_edi_cfdi_to_public === '1');
            order.l10n_mx_edi_usage = payload.l10n_mx_edi_usage;
            await this.orm.write("pos.order", [order.backendId], {
                'l10n_mx_edi_cfdi_to_public': order.l10n_mx_edi_cfdi_to_public,
                'l10n_mx_edi_usage': order.l10n_mx_edi_usage,
            });
        }
        return confirmed;
    }
});
