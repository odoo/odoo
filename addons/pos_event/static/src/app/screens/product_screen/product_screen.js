import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { EventConfiguratorPopup } from "@pos_event/app/components/popup/event_configurator_popup/event_configurator_popup";
import { EventRegistrationPopup } from "../../components/popup/event_registration_popup/event_registration_popup";
import { EventSlotSelectionPopup } from "../../components/popup/event_slot_selection_popup/event_slot_selection_popup";

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
        // the current order already validated registrations.
        // NB: Other orders event ticket registrations are not taken into account.
        const currentOrderEventRegistrations = (this.pos.getOrder()?.lines || []).reduce(
            (acc, line) => {
                const regs = (line.event_registration_ids.flat() || []).filter(
                    (reg) => reg.event_id?.id === event.id
                );
                return acc.concat(regs);
            },
            []
        );

        // Sold out alert: for event limit
        const eventCurrentAvailability = Math.max(
            event.seats_available - currentOrderEventRegistrations.length,
            0
        );
        const soldOutMessage = _t("No more seats available for this event");
        if (event.seats_limited && eventCurrentAvailability === 0) {
            this.notification.add(soldOutMessage, {
                type: "danger",
            });
            return;
        }

        const currentOrderRegCounts = currentOrderEventRegistrations.reduce(
            (acc, reg) => {
                const slotId = reg.event_slot_id?.id;
                const ticketId = reg.event_ticket_id?.id;
                // Per slot & ticket
                if (slotId && ticketId) {
                    if (!acc.perSlotTicket[ticketId]) {
                        acc.perSlotTicket[ticketId] = {};
                    }
                    acc.perSlotTicket[ticketId][slotId] =
                        (acc.perSlotTicket[ticketId][slotId] || 0) + 1;
                }
                // Per slot
                if (slotId) {
                    acc.perSlot[slotId] = (acc.perSlot[slotId] || 0) + 1;
                }
                // Per ticket
                if (ticketId) {
                    acc.perTicket[ticketId] = (acc.perTicket[ticketId] || 0) + 1;
                }
                return acc;
            },
            { perSlotTicket: {}, perSlot: {}, perTicket: {} }
        );

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
                const ticketsData = slotTickets[idx];
                const slotId = ticketsData[0];
                const ticketId = ticketsData[1];
                const currentCount = currentOrderRegCounts.perSlotTicket[ticketId]?.[slotId] ?? 0;
                if (!acc[ticketId]) {
                    acc[ticketId] = {};
                }
                if (!acc[ticketId][slotId]) {
                    acc[ticketId][slotId] = {};
                }
                if (availability === null) {
                    acc[ticketId][slotId] = "unlimited";
                } else if (typeof availability === "number") {
                    acc[ticketId][slotId] = availability - currentCount;
                } else {
                    acc[ticketId][slotId] = 0;
                }
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
            // Sum of ticket availabilities per slot.
            // Ex: Standard ticket: 2 seats available, VIP ticket: 1 seats available => total = 3
            //     If one is "unlimited" then total = "unlimited".
            const sumTicketAvailabilitiesPerSlot = Object.values(avaibilityByTicket).reduce(
                (acc, ticketAvailability) => {
                    Object.entries(ticketAvailability).forEach(([slotId, availability]) => {
                        if (acc[slotId] === "unlimited") {
                            return;
                        }
                        if (availability === "unlimited") {
                            acc[slotId] = "unlimited";
                        } else if (typeof availability === "number") {
                            acc[slotId] = (acc[slotId] || 0) + availability;
                        } else {
                            acc[slotId] = 0;
                        }
                    });
                    return acc;
                },
                {}
            );
            // Availability per slot is the minimum between:
            // - the sum of each slot ticket availabilities
            // - the slot seats_available which accounts for the event seats_max limitation (i.e. max X attendees per slot)
            // Both considering the current order registrations for the slot and tickets.
            const availabilityPerSlot = slots.reduce((acc, slot) => {
                const currentOrderSlotRegCount = currentOrderRegCounts.perSlot[slot.id] ?? 0;
                const slotAvailability = Math.max(
                    slot.seats_available - currentOrderSlotRegCount,
                    0
                );
                // "sumTicketAvailabilitiesPerSlot" already accounting for current order count
                const slotTotalTicketAvailability = sumTicketAvailabilitiesPerSlot[slot.id] ?? 0;

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
                acc[slot.id] = availability;
                return acc;
            }, {});
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
                const currentOrderTicketRegCount = currentOrderRegCounts.perTicket[ticket.id] ?? 0;
                if (ticket.seats_max === 0) {
                    // Ticket = unlimited seats
                    acc[ticket.id] = "unlimited";
                } else {
                    // Ticket = limited seats
                    acc[ticket.id] = ticket.seats_available - currentOrderTicketRegCount;
                }
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
            slotOrEventAvailability: slotResult?.slotAvailability || eventCurrentAvailability,
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

        const globalIdentificationAnswers = {};
        const identificationQuestionTypes = ["name", "email", "phone", "company_name"];

        const { globalSimpleChoice, globalTextAnswer } = Object.entries(result.byOrder).reduce(
            (acc, [questionId, answer]) => {
                const question = this.pos.models["event.question"].get(parseInt(questionId));
                if (
                    question.question_type === "simple_choice" &&
                    this.pos.models["event.question.answer"].get(parseInt(answer))
                ) {
                    acc.globalSimpleChoice[questionId] = answer;
                } else if (answer) {
                    acc.globalTextAnswer[questionId] = answer;
                    if (
                        identificationQuestionTypes.includes(question.question_type) &&
                        !(question.question_type in globalIdentificationAnswers)
                    ) {
                        globalIdentificationAnswers[question.question_type] = answer;
                    }
                }

                return acc;
            },
            { globalSimpleChoice: {}, globalTextAnswer: {} }
        );

        for (const [ticketId, data] of Object.entries(result.byRegistration)) {
            const ticket = this.pos.models["event.event.ticket"].get(parseInt(ticketId));
            const line = await this.pos.addLineToCurrentOrder({
                product_id: ticket.product_id,
                product_tmpl_id: ticket.product_id.product_tmpl_id,
                price_unit: ticket.price,
                price_type: "original",
                qty: data.length,
                event_ticket_id: ticket,
                event_slot_id: slotSelected,
            });

            for (const registration of data) {
                // Global answers have precedence for identification question types.
                const userData = { ...globalIdentificationAnswers };
                for (const [questionId, answer] of Object.entries(registration)) {
                    const question = this.pos.models["event.question"].get(parseInt(questionId));

                    if (
                        !question ||
                        !answer ||
                        !identificationQuestionTypes.includes(question.question_type) ||
                        question.question_type in userData
                    ) {
                        continue;
                    }

                    if (question.question_type === "email") {
                        userData.email = answer;
                    } else if (question.question_type === "phone") {
                        userData.phone = answer;
                    } else if (question.question_type === "name") {
                        userData.name = answer;
                    } else if (question.question_type === "company_name") {
                        userData.company_name = answer;
                    }
                }

                const { simpleChoice, textAnswer } = Object.entries(registration).reduce(
                    (acc, [questionId, answer]) => {
                        const question = this.pos.models["event.question"].get(
                            parseInt(questionId)
                        );
                        if (
                            question.question_type === "simple_choice" &&
                            this.pos.models["event.question.answer"].get(parseInt(answer))
                        ) {
                            acc.simpleChoice[questionId] = answer;
                        } else if (answer) {
                            acc.textAnswer[questionId] = answer;
                        }

                        return acc;
                    },
                    { simpleChoice: {}, textAnswer: {} }
                );
                // This will throw an error on creation if not possible (python constraint)
                this.pos.models["event.registration"].create({
                    ...userData,
                    event_id: event,
                    event_ticket_id: ticket,
                    event_slot_id: slotSelected,
                    pos_order_line_id: line,
                    partner_id: this.pos.getOrder().partner_id,
                    registration_answer_ids: Object.entries({
                        ...textAnswer,
                        ...globalTextAnswer,
                    }).map(([questionId, answer]) => [
                        "create",
                        {
                            question_id: this.pos.models["event.question"].get(
                                parseInt(questionId)
                            ),
                            value_text_box: answer,
                        },
                    ]),
                    registration_answer_choice_ids: Object.entries({
                        ...simpleChoice,
                        ...globalSimpleChoice,
                    }).map(([questionId, answer]) => [
                        "create",
                        {
                            question_id: this.pos.models["event.question"].get(
                                parseInt(questionId)
                            ),
                            value_answer_id: this.pos.models["event.question.answer"].get(
                                parseInt(answer)
                            ),
                        },
                    ]),
                });
            }
        }
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
