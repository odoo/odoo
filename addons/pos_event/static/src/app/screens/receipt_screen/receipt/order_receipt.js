import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { patch } from "@web/core/utils/patch";

patch(OrderReceipt.prototype, {
    _getAdditionalLineInfo(line) {
        const info = super._getAdditionalLineInfo(line);
        if (line.event_ticket_id) {
            info.push({
                class: "event-name",
                value: line.event_ticket_id.event_id.name,
                iclass: "fa-ticket",
            });
        }
        return info;
    },
});
