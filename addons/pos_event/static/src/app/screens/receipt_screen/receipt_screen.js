// Part of Odoo. See LICENSE file for full copyright and licensing details.
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";
import { useTrackedAsync } from "@point_of_sale/app/hooks/hooks";
import { useService } from "@web/core/utils/hooks";

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup(...arguments);

        this.report = useService("report");
        this.doPrintEventFull = useTrackedAsync(() => this.printEventFull());
        this.doPrintEventBadge = useTrackedAsync(() => this.printEventBadge());
    },
    async printEventFull() {
        const registrations = this.pos
            .getOrder()
            .eventRegistrations.map((reg) => this.pos.data.mapUuidToId(reg.id));
        await this.report.doAction("event.action_report_event_registration_full_page_ticket", [
            registrations,
        ]);
    },
    async printEventBadge() {
        const registrations = this.pos.getOrder().eventRegistrations;

        const smallBadgeRegistrations = registrations.filter(
            (reg) => reg.event_id.badge_format === "96x82"
        );
        const largeBadgeRegistrations = registrations.filter(
            (reg) => reg.event_id.badge_format === "96x134"
        );
        const nonBadgePrinterRegistrations = registrations.filter(
            (reg) => !["96x82", "96x134"].includes(reg.event_id.badge_format)
        );

        if (nonBadgePrinterRegistrations.length > 0) {
            await this.report.doAction(
                "event.action_report_event_registration_badge",
                nonBadgePrinterRegistrations.map((reg) => this.pos.data.mapUuidToId(reg.id))
            );
        }
        if (largeBadgeRegistrations.length > 0) {
            await this.report.doAction(
                "event.action_report_event_registration_badge_96x134",
                largeBadgeRegistrations.map((reg) => this.pos.data.mapUuidToId(reg.id))
            );
        }
        if (smallBadgeRegistrations.length > 0) {
            await this.report.doAction(
                "event.action_report_event_registration_badge_96x82",
                smallBadgeRegistrations.map((reg) => this.pos.data.mapUuidToId(reg.id))
            );
        }

        // Update the status to "attended" if we print the attendee badge
        if (registrations.length > 0) {
            registrations.update({ state: "done" });
        }
    },
});
