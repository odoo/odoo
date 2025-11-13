// Part of Odoo. See LICENSE file for full copyright and licensing details.
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";
import { useTrackedAsync } from "@point_of_sale/app/hooks/hooks";
import { useService } from "@web/core/utils/hooks";

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup(...arguments);

        this.report = useService("report");
        this.orm = useService("orm");
        this.doPrintEventFull = useTrackedAsync(() => this.printEventFull());
        this.doPrintEventBadge = useTrackedAsync(() => this.printEventBadge());
    },
    async printEventFull() {
        const registrations = this.currentOrder.eventRegistrations.map((reg) => reg.id);
        await this.report.doAction("event.action_report_event_registration_full_page_ticket", [
            registrations,
        ]);
    },
    async printEventBadge() {
        const registrations = this.currentOrder.eventRegistrations.map((reg) => reg.id);
        await this.report.doAction("event.action_report_event_registration_badge", [registrations]);

        // Update the status to "attended" if we print the attendee badge
        if (registrations.length > 0) {
            await this.orm.write("event.registration", registrations, { state: "done" });
        }
    },
});
