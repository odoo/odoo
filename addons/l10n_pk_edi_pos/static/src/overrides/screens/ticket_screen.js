import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";

patch(TicketScreen.prototype, {
    getFbrStatusClass(order) {
        return {
            "text-success": ["successful", "successful_demo"].includes(order.l10n_pk_edi_pos_state),
            "text-danger": order.l10n_pk_edi_pos_state === "unsuccessful",
            "text-muted": order.l10n_pk_edi_pos_state === "to_send",
        };
    },
});
