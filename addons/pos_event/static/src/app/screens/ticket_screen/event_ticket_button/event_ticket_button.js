// Part of Odoo. See LICENSE file for full copyright and licensing details.
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { useTrackedAsync } from "@point_of_sale/app/utils/hooks";

export class EventTicketButton extends Component {
    static template = "pos_event.EventTicketButton";
    static props = {
        order: Object,
        ticketFormat: String,
    };

    setup() {
        this.report = useService("report");
        this.doPrintEventTicket = useTrackedAsync(() => this.click());
    }

    async click() {
        if (!this.props.order) {
            return;
        }

        if (this.props.ticketFormat === "badge") {
            await this.printEventBadge();
        } else {
            await this.printEventFull();
        }
    }
    async printEventFull() {
        const registrations = this.props.order.eventRegistrations.map((reg) => reg.id);
        await this.report.doAction("event.action_report_event_registration_full_page_ticket", [
            registrations,
        ]);
    }
    async printEventBadge() {
        const registrations = this.props.order.eventRegistrations.map((reg) => reg.id);
        await this.report.doAction("event.action_report_event_registration_badge", [registrations]);
    }
}
