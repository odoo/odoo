// Part of Odoo. See LICENSE file for full copyright and licensing details.
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { EventRegistrationPopup } from "@pos_event/app/components/popup/event_registration_popup/event_registration_popup";
import { createRegistrationAnswer, extractRegistrationData } from "@pos_event/app/utils/event_util";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
    addLineToCurrentOrder(vals, opt = {}, configure = true) {
        const ticket = vals.sale_order_line_id?.event_ticket_id;
        if (ticket) {
            vals.event_ticket_id = ticket;
        }
        return super.addLineToCurrentOrder(vals, opt, configure);
    },
    async settleSO(saleOrder, orderFiscalPos) {
        // A ticket whose sale period is over is not loaded at session start
        const ticketIds = saleOrder.order_line
            .map((soLine) => soLine.raw.event_ticket_id)
            .filter((id) => id && !this.models["event.event.ticket"].get(id));
        if (ticketIds.length) {
            await this.data.read("event.event.ticket", ticketIds);
        }

        await super.settleSO(...arguments);

        // Attendees are registered when the sale order is confirmed, so a confirmed one has them
        // already. A quotation has none, and is only confirmed once this order is paid.
        if (!["draft", "sent"].includes(saleOrder.state)) {
            return;
        }
        for (const line of this.getOrder().lines) {
            if (line.event_ticket_id && line.sale_order_origin_id?.id === saleOrder.id) {
                await this.registerSettledAttendees(line);
            }
        }
    },
    async registerSettledAttendees(line) {
        const ticket = line.event_ticket_id;
        const slot = line.sale_order_line_id.event_slot_id;
        const quantity = Math.round(line.qty);
        const [available] = await this.data.call(
            "event.event",
            "get_slot_tickets_availability_pos",
            [ticket.event_id.id, [[slot?.id || false, ticket.id]]]
        );
        if (available !== null && available < quantity) {
            this.notification.add(_t("No more seats available for %s", ticket.name), {
                type: "danger",
            });
            return;
        }

        const result = await makeAwaitable(this.dialog, EventRegistrationPopup, {
            event: ticket.event_id,
            data: [{ product_id: line.product_id, ticket_id: ticket, qty: quantity }],
        });
        if (!result?.byRegistration) {
            return;
        }

        const { textAnswer: globalTextAnswer, userData: globalUserData } = extractRegistrationData(
            this.models,
            result.byOrder
        );
        for (const registration of Object.values(result.byRegistration).flat()) {
            const { textAnswer, userData } = extractRegistrationData(this.models, registration, {
                ...globalUserData,
            });

            this.models["event.registration"].create({
                ...userData,
                event_id: ticket.event_id,
                event_ticket_id: ticket,
                event_slot_id: slot,
                pos_order_line_id: line,
                // Keeps the sale order from registering the same attendees on confirmation
                sale_order_line_id: line.sale_order_line_id,
                registration_answer_ids: createRegistrationAnswer(
                    this.models,
                    Object.entries({ ...textAnswer, ...globalTextAnswer })
                ),
            });
        }
    },
});
