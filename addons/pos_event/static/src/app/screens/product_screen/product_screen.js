import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { patch } from "@web/core/utils/patch";
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

        if (product.event_id.seats_available === 0 && product.event_id.seats_limited) {
            this.notification.add("No more seats available for this event", {
                type: "danger",
            });
            return;
        }

        const event = product.event_id;
        const tickets = event.event_ticket_ids.filter(
            (ticket) => ticket.product_id && ticket.product_id.service_tracking === "event"
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
            const eventSeats = event.seats_limited ? event.seats_available : "unlimited";
            avaibilityByTicket = slotTicketAvailabilities.reduce((acc, availability, idx) => {
                const ticketsData = slotTickets[idx];
                const slotId = ticketsData[0];
                const ticketId = ticketsData[1];
                if (!acc[ticketId]) {
                    acc[ticketId] = {};
                }
                if (!acc[ticketId][slotId]) {
                    acc[ticketId][slotId] = {};
                }
                if (availability === null) {
                    acc[ticketId][slotId] = "unlimited";
                } else if (typeof availability === "number") {
                    acc[ticketId][slotId] = availability;
                } else {
                    acc[ticketId][slotId] = 0;
                }
                return acc;
            }, {});
            const isAvailable = Object.values(avaibilityByTicket).some((av) =>
                Object.values(av).some((a) => typeof a === "number" && a > 0)
            );
            if (!isAvailable || eventSeats === 0) {
                this.notification.add("All slots are booked out for this event.", {
                    type: "danger",
                });
                return;
            }
            const availabilityPerSlot = Object.values(avaibilityByTicket).reduce(
                (acc, ticketAvailability) => {
                    Object.entries(ticketAvailability).forEach(([slotId, availability]) => {
                        if (!acc[slotId]) {
                            acc[slotId] = 0;
                        } else if (acc[slotId] === "unlimited") {
                            return acc;
                        }
                        if (availability === "unlimited") {
                            acc[slotId] = "unlimited";
                        } else if (typeof availability === "number") {
                            acc[slotId] = Math.max(acc[slotId], availability);
                        } else {
                            acc[slotId] = Math.max(acc[slotId], 0);
                        }
                    });
                    return acc;
                },
                {}
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
                if (ticket.seats_max === 0) {
                    acc[ticket.id] = event.seats_limited ? event.seats_available : "unlimited";
                } else {
                    acc[ticket.id] = ticket.seats_available;
                }
                return acc;
            }, {});
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
