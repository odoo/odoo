/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { _t } from "@web/core/l10n/translation";

patch(TicketScreen.prototype, {
    //@override
    async addAdditionalRefundInfo(order, destinationOrder) {
        if (this.pos.config.l10n_es_edi_verifactu_required) {
            let selectionList = await this.orm.call("pos.order", "l10n_es_edi_verifactu_get_refund_reason_selection", []);
            selectionList = selectionList.filter((el) => {
                // Allow values that are not R5 only if a partner is specified; see Error [1189]:
                // Si TipoFactura es F1 o F3 o R1 o R2 o R3 o R4 el bloque Destinatarios tiene que estar cumplimentado.
                return destinationOrder.partner || (el[0] === 'R5')
            }).map((el) => {
                return { 'id': el[0], 'label': el[1], 'item': el[0]}
            })
            const { confirmed, payload } = await this.popup.add(SelectionPopup, {
                title: _t("Select the refund reason (Veri*Factu)"),
                list: selectionList,
            });
            if (payload && confirmed) {
                destinationOrder.l10n_es_edi_verifactu_refund_reason = payload;
                // Mark the new order as to invoice if the original order was invoiced.
                destinationOrder.to_invoice = order.to_invoice;
            }
        }
        super.addAdditionalRefundInfo(...arguments);
    },
});
