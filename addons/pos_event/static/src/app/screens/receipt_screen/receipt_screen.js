/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { useService } from "@web/core/utils/hooks";

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.report = useService("report");
    },
    _getRegistrationIds() {
        const eventLines = this.currentOrder.get_orderlines().filter(line => line.eventId);
        const registrationIds = eventLines.flatMap(line => line.eventRegistrationIds);
        return registrationIds;
    },
    async printFullPageTickets() {
        await this.report.doAction("event.action_report_event_registration_full_page_ticket", [
                this._getRegistrationIds(),
        ]);
    },
    async printFoldableBadge() {
        await this.report.doAction("event.action_report_event_registration_badge", [
                this._getRegistrationIds(),
        ]);
    },
});
