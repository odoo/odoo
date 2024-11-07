import { patch } from "@web/core/utils/patch";
import { EventRegistrationSummaryDialog } from "@event/client_action/event_registration_summary_dialog";

patch(EventRegistrationSummaryDialog.prototype, {
    get willAutoPrint() {
        return super.willAutoPrint && !this.registration.has_to_pay;
    },
});
