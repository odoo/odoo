// Part of Odoo. See LICENSE file for full copyright and licensing details.
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { patch } from "@web/core/utils/patch";
import { EventConfiguratorPopup } from "@pos_event/app/popup/event_configurator_popup/event_configurator_popup";
import { _t } from "@web/core/l10n/translation";
import { onWillStart } from "@odoo/owl";
import { EventRegistrationPopup } from "../../popup/event_registration_popup/event_registration_popup";

patch(ProductScreen.prototype, {
    setup() {
        super.setup();
        onWillStart(() => {
            this.pos.models["event.event"]
                .filter(
                    (event) =>
                        event.event_ticket_ids.length > 0 &&
                        event.event_ticket_ids.every(
                            (ticket) =>
                                ticket.product_id && ticket.product_id.service_tracking === "event"
                        )
                )
                .forEach((event) => {
                    const ticket = event.event_ticket_ids.sort(
                        (a, b) => a.product_id.get_price() - b.product_id.get_price()
                    )[0];

                    ticket.product_id._event_id = ticket.event_id;
                    return ticket.product_id;
                });
        });
    },
    get products() {
        const products = super.products;
        return [...products].filter((p) => p.service_tracking !== "event" || p._event_id);
    },
    getProductName(product) {
        if (!product._event_id) {
            return super.getProductName(product);
        }

        return product._event_id.name;
    },
    getProductPrice(product) {
        if (!product._event_id) {
            return super.getProductPrice(product);
        }

        const event = product._event_id;
        const minPrice = Math.min(
            ...event.event_ticket_ids.map((ticket) => this.pos.getProductPrice(ticket.product_id))
        );

        return _t("From %s", this.env.utils.formatCurrency(minPrice));
    },
    getProductImage(product) {
        if (!product._event_id) {
            return super.getProductImage(product);
        }

        return `/web/image?model=event.event&id=${product._event_id.id}&field=image_1024&unique=${product._event_id.write_date}`;
    },
    async addProductToOrder(product) {
        if (!product._event_id) {
            return await super.addProductToOrder(product);
        }

        if (product._event_id.seats_available === 0 && product._event_id.seats_limited) {
            this.notification.add("No more seats available for this event", {
                type: "danger",
            });
            return;
        }

        const event = product._event_id;
        const tickets = event.event_ticket_ids.filter(
            (ticket) => ticket.product_id && ticket.product_id.service_tracking === "event"
        );

        const result = await makeAwaitable(this.dialog, EventConfiguratorPopup, {
            tickets: tickets,
        });

        if (!result || !result.length) {
            this.notification.add("No more ticket available", {
                type: "warning",
            });
            return;
        }

        const registrations = await makeAwaitable(this.dialog, EventRegistrationPopup, {
            data: result,
        });

        if (!registrations || !Object.keys(registrations).length) {
            return;
        }

        for (const [ticketId, data] of Object.entries(registrations)) {
            const ticket = this.pos.models["event.event.ticket"].get(parseInt(ticketId));
            const line = await this.pos.addLineToCurrentOrder({
                product_id: ticket.product_id,
                qty: data.length,
                event_ticket_id: ticket,
            });

            for (const registration of data) {
                this.pos.models["event.registration"].create({
                    event_id: event,
                    event_ticket_id: ticket,
                    pos_order_line_id: line,
                    ...registration,
                });
            }
        }
    },
});
