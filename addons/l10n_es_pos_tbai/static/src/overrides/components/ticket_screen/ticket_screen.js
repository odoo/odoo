/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { _t } from "@web/core/l10n/translation";

patch(TicketScreen.prototype, {
    //@override
    async addAdditionalRefundInfo(order, destinationOrder) {
        if (this.pos.config.is_spanish && order.state == "invoiced") {
            let selectionList = await this.orm.call("account.move", "get_refund_reason_list", []);
            selectionList = selectionList.map((el) => {
                return { 'id': el[0], 'label': el[1], 'item': el[0]}
            })
            const { confirmed, payload } = await this.popup.add(SelectionPopup, {
                title: _t("Select the refund reason"),
                list: selectionList,
            });
            if (payload && confirmed) {
                destinationOrder.l10n_es_tbai_refund_reason = payload;
                destinationOrder.to_invoice = true;
            }
        }
        super.addAdditionalRefundInfo(...arguments);
    },
});
