/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { useService } from "@web/core/utils/hooks";

patch(TicketScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.report = useService("report");
    },
    _getRegistrationIds() {
        const eventLines = this.getSelectedOrder().get_orderlines().filter(line => line.eventId);
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
    async onDoRefund() {
        const orderline = this.getSelectedOrder().orderlines.find((line) => line.id == this.getSelectedOrderlineId());
        if (orderline.product.detailed_type === 'event'){
            return;
        }
        return super.onDoRefund(...arguments);
    }
});
