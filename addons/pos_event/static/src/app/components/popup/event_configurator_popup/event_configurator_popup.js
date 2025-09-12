// Part of Odoo. See LICENSE file for full copyright and licensing details.
import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { ProductCard } from "@point_of_sale/app/components/product_card/product_card";
import { NumericInput } from "@point_of_sale/app/components/inputs/numeric_input/numeric_input";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

const { DateTime } = luxon;

export class EventConfiguratorPopup extends Component {
    static template = "pos_event.EventConfiguratorPopup";
    static props = ["tickets", "getPayload", "close", "slotResult", "availabilityPerTicket"];
    static components = {
        Dialog,
        ProductCard,
        NumericInput,
    };
    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
        this.state = useState({});
        this.slotAvailability = this.props.slotResult?.slotAvailability;
        this.slotId = this.props.slotResult?.slotId;

        for (const ticket of this.props.tickets) {
            this.state[ticket.id] = {
                qty: 0,
            };
        }
    }
    get dialogTitle() {
        const event = this.props.tickets[0].event_id;
        if (event.seats_limited) {
            return _t("Select tickets for %(event)s (%(seats)s seats available%(suffix)s)", {
                event: event.name,
                seats: this.slotId ? this.slotAvailability : event.seats_available,
                suffix: this.slotId ? _t(" for this slot") : "",
            });
        }
        return _t("Select tickets for %(event)s", { event: event.name });
    }
    getTicketMaxQty(ticket) {
        if (typeof this.props.availabilityPerTicket[ticket.id] !== "object") {
            return this.props.availabilityPerTicket[ticket.id];
        }
        const ticketAvailability = this.props.availabilityPerTicket[ticket.id][this.slotId];
        const existingUnsyncRegistration = this.pos.models["event.registration"].filter(
            (r) => !r.isSynced && r.event_slot_id.id === this.slotId
        );
        if (ticketAvailability === "unlimited") {
            return ticket.event_id.seats_limited ? ticket.event_id.seats_available : "unlimited";
        }
        return Math.max(ticketAvailability - existingUnsyncRegistration.length, 0);
    }
    confirm() {
        const data = [];
        for (const [ticketId, { qty }] of Object.entries(this.state)) {
            if (qty > 0) {
                const ticket = this.pos.models["event.event.ticket"].get(parseInt(ticketId));
                const available = this.ticketIsAvailable(ticket);

                if (!available) {
                    this.dialog.add(AlertDialog, {
                        title: _t("Error"),
                        body: _t(
                            "The selected ticket (%s) is not available. Please select a different ticket.",
                            [ticket.name]
                        ),
                    });
                    this.props.close();
                    return;
                }

                data.push({
                    product_id: ticket.product_id,
                    ticket_id: ticket,
                    qty,
                });
            }
        }

        this.props.getPayload(data);
        this.props.close();
    }
    cancel() {
        this.props.close();
    }
    ticketIsAvailable(ticket) {
        const dateTimeNow = DateTime.now();

        const eventSaleEnd =
            !ticket.end_sale_datetime || ticket.end_sale_datetime.ts > dateTimeNow.ts;
        const eventSaleStart =
            !ticket.start_sale_datetime || ticket.start_sale_datetime.ts < dateTimeNow.ts;
        if (!eventSaleStart || !eventSaleEnd) {
            return false;
        }

        const ticketMaxQty = this.getTicketMaxQty(ticket);
        return (
            ticketMaxQty === "unlimited" ||
            (ticketMaxQty > 0 && ticketMaxQty >= this.state[ticket.id].qty)
        );
    }
}
