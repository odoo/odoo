import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { patch } from "@web/core/utils/patch";
import { EventConfiguratorPopup } from "@pos_event/app/components/popup/event_configurator_popup/event_configurator_popup";
import { EventRegistrationPopup } from "../../components/popup/event_registration_popup/event_registration_popup";
import { EventSlotSelectionPopup } from "../../components/popup/event_slot_selection_popup/event_slot_selection_popup";
import { _t } from "@web/core/l10n/translation";

const { DateTime } = luxon;

patch(ProductScreen.prototype, {
    get products() {
        const products = super.products;
        return [...products].filter((p) => p.service_tracking !== "event");
    },
    getProductImage(product) {
        if (!product.event_id) {
            return super.getProductImage(product);
        }

        return `/web/image?model=event.event&id=${product.event_id.id}&field=image_1024&unique=${product.event_id.write_date}`;
    },
    async addProductToOrder(product) {
        if (!product.event_id) {
            return await super.addProductToOrder(product);
        }

        const event = product.event_id;
        const tickets = event.event_ticket_ids.filter(
            (ticket) => ticket.product_id && ticket.product_id.service_tracking === "event"
        );

        // Used to dynamically update the event ticket availabilities depending on
        // the unsynced registrations of all the orders (open, or paid but not synced yet).
        // Synced registrations are already counted in the seats availability loaded in the PoS.
        // NB: everything is computed from the data loaded in the PoS so it works offline.
        const openOrdersEventRegistrations = this.pos.models["pos.order"]
            .getAll()
            .flatMap((order) => order.lines)
            .flatMap((line) => line.event_registration_ids.flat())
            .filter((reg) => reg.event_id?.id === event.id && !reg.isSynced);

        // Sold out alert: for event limit
        const eventCurrentAvailability = Math.max(
            event.seats_available - openOrdersEventRegistrations.length,
            0
        );
        const soldOutMessage = _t("No more seats available for this event");
        if (event.seats_limited && eventCurrentAvailability === 0) {
            this.notification.add(soldOutMessage, {
                type: "danger",
            });
            return;
        }

        // Number of unsynced registrations for a slot and/or a ticket
        const countRegs = (slotId, ticketId) =>
            openOrdersEventRegistrations.filter(
                (reg) =>
                    (!slotId || reg.event_slot_id?.id === slotId) &&
                    (!ticketId || reg.event_ticket_id?.id === ticketId)
            ).length;

        // Multi Slot
        let avaibilityByTicket = {};
        let slotResult = {};
        let slotSelected;
        let slotTicketAvailabilities = {};
        if (event.is_multi_slots) {
            // Updating data in case of event change
            await this.pos.data.read(
                "event.event",
                [event.id],
                ["event_slot_ids", "seats_available", "seats_limited"]
            );
            await this.pos.data.read(
                "event.slot",
                event.event_slot_ids.map((slot) => slot.id)
            );
            const slotTickets = [];
            const slots = event.event_slot_ids.filter(
                (slot) => slot.start_datetime > DateTime.now()
            );
            for (const ticket of tickets) {
                for (const slot of slots) {
                    slotTickets.push([slot.id, ticket.id]);
                }
            }
            slotTicketAvailabilities = await this.pos.data.call(
                "event.event",
                "get_slot_tickets_availability_pos",
                [event.id, slotTickets]
            );
            avaibilityByTicket = slotTicketAvailabilities.reduce((acc, availability, idx) => {
                const [slotId, ticketId] = slotTickets[idx];
                const currentCount = countRegs(slotId, ticketId);
                // Maximum number of ticket the user can select in the selection box.
                // NB: This number doesn't refer to a global limit for the order.
                const ticketSelectionMax =
                    tickets.find((t) => t.id === ticketId)?.limit_max_per_order ?? 0;

                acc[ticketId] ??= {};
                let slotTicketAvailability;
                if (availability === null) {
                    slotTicketAvailability = "unlimited";
                } else if (typeof availability === "number") {
                    slotTicketAvailability = availability - currentCount;
                    if (event.seats_limited && event.seats_max) {
                        // The slot limit is considered into the 'availability' but only the unsynced registrations
                        // for this ticket 'currentCount' were subtracted. Also considering that the other tickets
                        // unsynced registrations can reduce the slot limit.
                        const slotSeats = slots.find((slot) => slot.id === slotId).seats_available;
                        slotTicketAvailability = Math.min(
                            slotTicketAvailability,
                            slotSeats - countRegs(slotId)
                        );
                    }
                } else {
                    slotTicketAvailability = 0;
                }
                if (ticketSelectionMax > 0) {
                    slotTicketAvailability =
                        slotTicketAvailability === "unlimited"
                            ? ticketSelectionMax
                            : Math.min(ticketSelectionMax, slotTicketAvailability);
                }
                if (slotTicketAvailability !== "unlimited") {
                    slotTicketAvailability = Math.max(0, slotTicketAvailability);
                }
                acc[ticketId][slotId] = slotTicketAvailability;
                return acc;
            }, {});
            const isAvailable = Object.values(avaibilityByTicket).some((av) =>
                Object.values(av).some((a) => (typeof a === "number" && a > 0) || a === "unlimited")
            );
            // Sold out alert: for slot ticket limits
            if (!isAvailable) {
                this.notification.add(soldOutMessage, {
                    type: "danger",
                });
                return;
            }
            // Availability per slot is the minimum between:
            // - the sum of each slot ticket availabilities
            // - the slot seats_available which accounts for the event seats_max limitation (i.e. max X attendees per slot)
            // Both considering the current order registrations for the slot and tickets.
            const availabilityPerSlot = Object.fromEntries(
                slots.map((slot) => {
                    const slotAvailability = Math.max(slot.seats_available - countRegs(slot.id), 0);
                    // Sum of ticket availabilities for the slot, already accounting for current order count.
                    // Ex: Standard ticket: 2 seats available, VIP ticket: 1 seats available => total = 3
                    //     If one is "unlimited" then total = "unlimited".
                    const ticketAvailabilities = tickets.map(
                        (ticket) => avaibilityByTicket[ticket.id][slot.id]
                    );
                    const slotTotalTicketAvailability = ticketAvailabilities.includes("unlimited")
                        ? "unlimited"
                        : ticketAvailabilities.reduce((sum, availability) => sum + availability, 0);

                    let availability = 0;
                    if (!event.seats_limited) {
                        // Slot = unlimited seats
                        availability = slotTotalTicketAvailability;
                    } else if (slotTotalTicketAvailability === "unlimited") {
                        // Slot = limited seats, Tickets = total is unlimited
                        availability = slotAvailability;
                    } else {
                        // Slot = limited seats, Tickets = total is limited
                        availability = Math.max(
                            Math.min(slotAvailability, slotTotalTicketAvailability),
                            0
                        );
                    }
                    return [slot.id, availability];
                })
            );
            slotResult = await makeAwaitable(this.dialog, EventSlotSelectionPopup, {
                availabilityPerSlot: availabilityPerSlot,
                event: event,
            });
            if (!slotResult?.slotId) {
                return;
            }
            slotSelected = this.pos.models["event.slot"].get(slotResult.slotId);
        } else {
            avaibilityByTicket = tickets.reduce((acc, ticket) => {
                const openOrdersTicketRegCount = countRegs(null, ticket.id);
                // Maximum number of ticket the user can select in the selection box.
                // NB: This number doesn't refer to a global limit for the order
                const ticketSelectionMax = ticket.limit_max_per_order ?? 0;
                let availability;
                if (ticket.seats_max === 0) {
                    // Ticket = unlimited seats
                    availability = "unlimited";
                } else {
                    // Ticket = limited seats
                    availability = ticket.seats_available - openOrdersTicketRegCount;
                }
                if (ticketSelectionMax > 0) {
                    availability =
                        availability === "unlimited"
                            ? ticketSelectionMax
                            : Math.min(ticketSelectionMax, availability);
                }
                if (availability !== "unlimited") {
                    availability = Math.max(0, availability);
                }
                acc[ticket.id] = availability;
                return acc;
            }, {});
            const isAvailable = Object.values(avaibilityByTicket).some(
                (av) => (typeof av === "number" && av > 0) || av === "unlimited"
            );
            // Sold out alert: for ticket limits
            if (!isAvailable) {
                this.notification.add(soldOutMessage, {
                    type: "danger",
                });
                return;
            }
        }

        const ticketResult = await makeAwaitable(this.dialog, EventConfiguratorPopup, {
            availabilityPerTicket: avaibilityByTicket,
            slotResult: slotResult,
            tickets: tickets,
        });
        if (!ticketResult || !ticketResult.length) {
            return;
        }

        const result = await makeAwaitable(this.dialog, EventRegistrationPopup, {
            event: event,
            data: ticketResult,
        });

        if (!result || !result.byRegistration || !Object.keys(result.byRegistration).length) {
            return;
        }

        const { textAnswer: globalTextAnswer, userData: globalUserData } =
            this.extractRegistrationData(result.byOrder);

        for (const [ticketId, data] of Object.entries(result.byRegistration)) {
            const ticket = this.pos.models["event.event.ticket"].get(parseInt(ticketId));
            const priceExtra = ticket.price - ticket.product_id.lst_price;
            const priceUnit = ticket.product_id.getPrice(
                this.pos.getOrder().pricelist_id,
                1,
                priceExtra,
                false,
                ticket.product_id
            );
            const line = await this.pos.addLineToCurrentOrder({
                product_id: ticket.product_id,
                product_tmpl_id: ticket.product_id.product_tmpl_id,
                price_unit: priceUnit,
                price_extra: priceExtra,
                price_type: "original",
                qty: data.length,
                event_ticket_id: ticket,
                event_slot_id: slotSelected,
            });

            for (const registration of data) {
                const { textAnswer, userData } = this.extractRegistrationData(registration, {
                    ...globalUserData,
                });

                // This will throw an error on creation if not possible (python constraint)
                this.pos.models["event.registration"].create({
                    ...userData,
                    event_id: event,
                    event_ticket_id: ticket,
                    event_slot_id: slotSelected,
                    pos_order_line_id: line,
                    partner_id: this.pos.getOrder().partner_id,
                    registration_answer_ids: this.createRegistrationAnswer(
                        Object.entries({ ...textAnswer, ...globalTextAnswer })
                    ),
                });
            }
        }
    },
    createRegistrationAnswer(textAnswers) {
        return textAnswers.map(([questionId, answer]) => {
            const ansId = this.pos.models["event.question.answer"].get(parseInt(answer));
            return [
                "create",
                {
                    question_id: this.pos.models["event.question"].get(parseInt(questionId)),
                    ...(ansId ? { value_answer_id: ansId } : { value_text_box: answer }),
                },
            ];
        });
    },
    extractRegistrationData(questions, userData = {}) {
        const IDENTIFICATION_QUESTION_TYPES = new Set(["name", "email", "phone", "company_name"]);

        return Object.entries(questions).reduce(
            (acc, [qId, answer]) => {
                if (!answer) {
                    return acc;
                }

                const question = this.pos.models["event.question"].get(parseInt(qId));
                if (!question) {
                    return acc;
                }

                acc.textAnswer[qId] = answer;
                if (IDENTIFICATION_QUESTION_TYPES.has(question.question_type)) {
                    userData[question.question_type] ??= answer;
                }

                return acc;
            },
            { textAnswer: {}, userData }
        );
    },
    onMouseDown(event, product) {
        if (product.event_id) {
            return;
        }
        return super.onMouseDown(event, product);
    },
    onTouchStart(product) {
        if (product.event_id) {
            return;
        }
        return super.onTouchStart(product);
    },
});
