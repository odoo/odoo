/** @odoo-module **/

import PaymentScreen from "@point_of_sale/js/Screens/PaymentScreen/PaymentScreen";
import Registries from "@point_of_sale/js/Registries";

export const PosLoyaltyPaymentScreen = (PaymentScreen) => class extends PaymentScreen {
    //@override
    async validateOrder(isForceValidate) { // todo take into account when validation of order failed, what to do ?
        const order = this.env.pos.get_order();
        const eventLines = order.get_orderlines().filter(line => line.eventId);
        if (eventLines.length > 0) {
            const registrationVals = [];
            const partnerId = order.get_partner().id;
            //  In case we have a situation where we have one orderline with a qty of 2
            //  and one orderline with a qty of -1, we should create only one registration in total.
            //  We create a counter for every ticket to know exactly how many registration need to be made
            const tickedIdCounter = {};
            for (const line of eventLines) {
                if (line.eventTicketId in tickedIdCounter) {
                    tickedIdCounter[line.eventTicketId] += line.quantity;
                } else {
                    tickedIdCounter[line.eventTicketId] = line.quantity
                }
            }
            // We create the registrations values based on the counter.
            let remainingCounter = { ...tickedIdCounter };
            for (const line of eventLines) {
                const registrationQty = remainingCounter[line.eventTicketId] - line.quantity >= 0 ? line.quantity : remainingCounter[line.eventTicketId];
                remainingCounter[line.eventTicketId] -= registrationQty;
                for (let i = 0; i < registrationQty; i++) {
                    registrationVals.push({
                        event_id: line.eventId,
                        event_ticket_id: line.eventTicketId,
                        partner_id: partnerId,
                    });
                }
            }
            //todo improve registration in the event app because this doesn"t take concurrency problem into account ...
            const registrationIds = await this.rpc({
                model: "event.registration",
                method: "create",
                args: [registrationVals],
            })

            // Assigning the registration ids to the order lines using the same mechanism as above. Since we are
            // using array which are ordered, the received ids can be attributed using the same order
            remainingCounter = { ...tickedIdCounter };
            const remainingRegistrationIds = [...registrationIds];
            for (const line of eventLines) {
                const registrationQty = remainingCounter[line.eventTicketId] - line.quantity >= 0 ? line.quantity : remainingCounter[line.eventTicketId];
                remainingCounter[line.eventTicketId] -= registrationQty;
                const registrationToSet = remainingRegistrationIds.splice(0, registrationQty);
                if (registrationToSet.length > 0) {
                    line.setEventRegistrationIds(registrationToSet);
                }
            }
        }
        return await super.validateOrder(...arguments);
    }

    /**
     * @override
     */
    // async _postPushOrderResolve(order, server_ids) {
    // }
};

Registries.Component.extend(PaymentScreen, PosLoyaltyPaymentScreen);
