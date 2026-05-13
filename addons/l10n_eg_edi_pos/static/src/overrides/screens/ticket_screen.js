import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(TicketScreen.prototype, {
    get showEtaStatus() {
        return this.pos.config.l10n_eg_edi_pos_enable;
    },
    etaStatus(order) {
        switch (order?.l10n_eg_edi_pos_state) {
            case "to_send":
                return _t("To Send");
            case "sent":
                return _t("Sent");
            case "sent_test":
                return _t("Sent (Test)");
            case "error":
                return _t("Error");
            case "error_test":
                return _t("Error (Test)");
            case "rejected":
                return _t("Rejected");
            case "rejected_test":
                return _t("Rejected (Test)");
            default:
                return "";
        }
    },
});
