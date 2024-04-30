// Part of Odoo. See LICENSE file for full copyright and licensing details.
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";
import { useTrackedAsync } from "@point_of_sale/app/utils/hooks";
import { useService } from "@web/core/utils/hooks";

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup(...arguments);

        this.report = useService("report");
        this.doPrintEventFull = useTrackedAsync(() => this.printEventFull());
        this.doPrintEventBadge = useTrackedAsync(() => this.printEventBadge());
    },
    async printEventFull() {
        const registrations = this.pos.get_order().eventRegistrations.map((reg) => reg.id);
        await this.report.doAction("event.action_report_event_registration_full_page_ticket", [
            registrations,
        ]);
    },
    async printEventBadge() {
        const registrations = this.pos.get_order().eventRegistrations.map((reg) => reg.id);
        await this.report.doAction("event.action_report_event_registration_badge", [registrations]);
    },
});
