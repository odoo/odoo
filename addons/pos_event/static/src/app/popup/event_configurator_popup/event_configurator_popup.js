// Part of Odoo. See LICENSE file for full copyright and licensing details.
import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
import { NumericInput } from "@point_of_sale/app/generic_components/inputs/numeric_input/numeric_input";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { deserializeDateTime } from "@web/core/l10n/dates";

const { DateTime } = luxon;

export class EventConfiguratorPopup extends Component {
    static template = "pos_event.EventConfiguratorPopup";
    static props = ["tickets", "getPayload", "close"];
    static components = {
        Dialog,
        ProductCard,
        NumericInput,
    };
    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
        this.state = useState({});

        for (const ticket of this.props.tickets) {
            this.state[ticket.id] = {
                qty: 0,
            };
        }
    }
    get dialogTitle() {
        const event = this.props.tickets[0].event_id;
        let title = _t("Select tickets for %s", [event.name]);

        if (event.seats_limited) {
            title += _t(" (%s seats available)", [event.seats_available]);
        }

        return title;
    }
    getTicketMaxQty(ticket) {
        const event = ticket.event_id;
        const maxTicket = ticket.seats_available - this.getOrderAlreadyBooked(ticket);

        if ((event.seats_limited && event.seats_available < maxTicket) || ticket.seats_max === 0) {
            return event.seats_available;
        }

        return maxTicket;
    }
    getProductProxy(productId) {
        return this.pos.models["product.product"].get(productId);
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
    getOrderAlreadyBooked(ticket) {
        return this.pos
            .get_order()
            .lines.filter((l) => l.event_ticket_id?.id === ticket.id)
            .reduce((acc, l) => (acc += l.qty), 0);
    }
    ticketIsAvailable(ticket) {
        const dateTimeNow = DateTime.now();
        const bookedTicket = this.getOrderAlreadyBooked(ticket) + this.state[ticket.id].qty;
        const eventAvailable =
            !ticket.event_id?.seats_limited || bookedTicket <= ticket.event_id.seats_available;

        const eventSaleEnd =
            !ticket.end_sale_datetime ||
            deserializeDateTime(ticket.end_sale_datetime).ts > dateTimeNow.ts;
        const eventSaleStart =
            !ticket.start_sale_datetime ||
            deserializeDateTime(ticket.start_sale_datetime).ts < dateTimeNow.ts;

        if (!eventSaleStart || !eventSaleEnd) {
            return false;
        }

        if (ticket.seats_max === 0 && eventAvailable) {
            return true;
        }

        return ticket.seats_available >= bookedTicket && eventAvailable;
    }
}
