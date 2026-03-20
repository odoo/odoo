// Part of Odoo. See LICENSE file for full copyright and licensing details.
import { patch } from "@web/core/utils/patch";
import { useTrackedAsync } from "@point_of_sale/app/hooks/hooks";
import { useService } from "@web/core/utils/hooks";
import { PrintPopup } from "@point_of_sale/app/components/popups/print_popup/print_popup";

patch(PrintPopup.prototype, {
    setup() {
        this.report = useService("report");
        this.doPrintEventFull = useTrackedAsync(() => this.printEventFull());
        this.doPrintEventBadge = useTrackedAsync(() => this.printEventBadge());
        super.setup(...arguments);
    },
    get printList() {
        const list = super.printList;
        if (this.order.eventRegistrations.length > 0) {
            list.push({
                label: "Print Full Page Ticket",
                method: () => this.doPrintEventFull.call(),
                status: this.doPrintEventFull.status,
                icon: "fa-ticket",
                isPrimary: false,
            });
            list.push({
                label: "Print Badge",
                method: () => this.doPrintEventBadge.call(),
                status: this.doPrintEventBadge.status,
                icon: "fa-id-badge",
                isPrimary: false,
            });
        }
        return list;
    },
    async printEventFull() {
        const registrations = this.order.eventRegistrations.map((reg) => reg.id);
        await this.report.doAction("event.action_report_event_registration_full_page_ticket", [
            registrations,
        ]);
    },
    async printEventBadge() {
        const registrations = this.order.eventRegistrations.map((reg) => reg.id);
        await this.report.doAction("event.action_report_event_registration_badge", [registrations]);

        // Update the status to "attended" if we print the attendee badge
        if (registrations.length > 0) {
            await this.pos.data.ormWrite("event.registration", registrations, { state: "done" });
        }
    },
});
