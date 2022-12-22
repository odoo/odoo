/** @odoo-module */

import ReceiptScreen from "@point_of_sale/js/Screens/ReceiptScreen/ReceiptScreen";
import Registries from "@point_of_sale/js/Registries";

export const PosEventReceiptScreen = (ReceiptScreen) => class extends ReceiptScreen {

    _getRegistrationIds() {
        const eventLines = this.currentOrder.get_orderlines().filter(line => line.eventId);
        const registrationIds = eventLines.flatMap(line => line.eventRegistrationIds);
        return registrationIds;
    }
    async printFullPageTickets() {
        await this.env.legacyActionManager.do_action("event.action_report_event_registration_full_page_ticket", {
            additional_context: {
                active_ids: this._getRegistrationIds(),
            },
        });
    }
    async printFoldableBadge() {
        await this.env.legacyActionManager.do_action("event.action_report_event_registration_foldable_badge", {
            additional_context: {
                active_ids: this._getRegistrationIds(),
            },
        });
    }
};
Registries.Component.extend(ReceiptScreen, PosEventReceiptScreen);
