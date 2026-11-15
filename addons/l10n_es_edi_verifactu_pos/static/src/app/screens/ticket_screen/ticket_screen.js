import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

patch(TicketScreen.prototype, {
    async addAdditionalRefundInfo(order, destinationOrder) {
        if (this.pos.company.l10n_es_edi_verifactu_required) {
            destinationOrder.l10n_es_invoice_type = "R5";
        }
        await super.addAdditionalRefundInfo(...arguments);
    },
});
