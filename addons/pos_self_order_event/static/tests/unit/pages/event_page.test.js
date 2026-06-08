/** @odoo-module **/

import { test, describe, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { EventPage } from "@pos_self_order_event/app/pages/event_page/event_page";
import { setupSelfPosEnv } from "@pos_self_order/../tests/unit/utils";
import { definePosSelfModels } from "@pos_self_order/../tests/unit/data/generate_model_definitions";

definePosSelfModels();

describe("EventPage Component", () => {
    test("validateQuestion", async () => {
        const store = await setupSelfPosEnv();
        const models = store.models;
        const event = models["event.event"].get(1);
        const comp = await mountWithCleanup(EventPage, {
            props: { eventTemplate: event },
        });

        expect(comp.validateQuestion({ question_type: "email" }, "invalid")).toBe(false);
        expect(comp.validateQuestion({ question_type: "email" }, "test@example.com")).toBe(true);
        expect(comp.validateQuestion({ question_type: "phone" }, "+1234567890")).toBe(true);
        expect(comp.validateQuestion({ question_type: "phone" }, "abc")).toBe(false);
        expect(comp.validateQuestion({ is_mandatory_answer: true }, "")).toBe(false);
        expect(comp.validateQuestion({ is_mandatory_answer: true }, "answer")).toBe(true);
    });

    test("onStepClicked", async () => {
        const store = await setupSelfPosEnv();
        const models = store.models;
        const event = models["event.event"].get(1);

        const comp = await mountWithCleanup(EventPage, {
            props: { eventTemplate: event },
        });

        let [firstStep, secondStep, thirdStep] = comp.steps;
        comp.state.selectedStep = firstStep;

        comp.state.selectedSlot = 1;
        comp.next();
        expect(comp.state.selectedStep).toEqual(secondStep);

        comp.back();
        expect(comp.state.selectedStep).toEqual(firstStep);

        comp.state.selectedSlot = null;
        comp.state.selectedStep = firstStep;
        comp.onStepClicked(1);
        expect(comp.state.selectedStep).toEqual(firstStep);

        comp.state.selectedSlot = 1;
        comp.onStepClicked(1);
        expect(comp.state.selectedStep).toEqual(secondStep);

        comp.state.ticketQuantities = { [event.event_ticket_ids[0].id]: 1 };
        comp.next();
        expect(comp.state.selectedStep).toEqual(thirdStep);

        comp.state.ticketQuantities = {};
        comp.state.selectedStep = secondStep;
        comp.onStepClicked(2);
        expect(comp.state.selectedStep).toEqual(secondStep);

        comp.state.ticketQuantities = { [event.event_ticket_ids[0].id]: 1 };
        comp.onStepClicked(2);
        expect(comp.state.selectedStep).toEqual(thirdStep);

        // Event without multiple slots
        event.event_slot_ids = [];
        [firstStep, secondStep] = comp.steps;
        comp.state.selectedStep = firstStep;

        comp.state.ticketQuantities = { [event.event_ticket_ids[0].id]: 1 };
        comp.next();
        expect(comp.state.selectedStep).toEqual(secondStep);

        comp.back();
        expect(comp.state.selectedStep).toEqual(firstStep);

        comp.state.ticketQuantities = {};
        comp.state.selectedStep = firstStep;
        comp.onStepClicked(1);
        expect(comp.state.selectedStep).toEqual(firstStep);

        comp.state.ticketQuantities = { [event.event_ticket_ids[0].id]: 1 };
        comp.onStepClicked(1);
        expect(comp.state.selectedStep).toEqual(secondStep);
    });

    test("slotAvailabilityText", async () => {
        const store = await setupSelfPosEnv();
        const models = store.models;
        const event = models["event.event"].get(1);
        const comp = await mountWithCleanup(EventPage, {
            props: { eventTemplate: event },
        });
        const slot = models["event.slot"].get(event.event_slot_ids[0].id);
        expect(comp.slotAvailabilityText(slot)).toBe("5 seats available");
        slot.seats_available = 0;
        expect(comp.slotAvailabilityText(slot)).toBe("No seats available");
    });

    test("seatAvailability", async () => {
        const store = await setupSelfPosEnv();
        const models = store.models;
        const event = models["event.event"].get(1);
        const comp = await mountWithCleanup(EventPage, {
            props: { eventTemplate: event },
        });
        event.is_multi_slots = false;
        const ticket = comp.eventTickets[0];
        expect(comp.seatAvailability(ticket)).toBe(true);
        event.seats_available = 0;
        event.seats_limited = false;
        expect(comp.seatAvailability(ticket)).toBe(true);
        event.seats_available = 0;
        event.seats_limited = true;
        expect(comp.seatAvailability(ticket)).toBe(false);

        event.is_multi_slots = true;
        comp.state.selectedSlot = 1;
        comp.state.slotTicketAvailabilities = {
            [ticket.id]: { 1: 5 },
        };
        expect(comp.seatAvailability(ticket)).toBe(true);
    });

    test("changeQuantity", async () => {
        const store = await setupSelfPosEnv();
        const models = store.models;
        const event = models["event.event"].get(1);

        const comp = await mountWithCleanup(EventPage, {
            props: { eventTemplate: event },
        });

        comp.selfOrder = store;
        comp.canIncreaseTicket = () => true;

        expect(Object.keys(comp.state.ticketQuantities)).toHaveLength(0);
        expect(comp.state.totalPrice).toBe(0);

        comp.changeQuantity(1, true);
        expect(comp.state.ticketQuantities[1]).toBe(1);
        expect(comp.state.totalPrice).toBe(100);
        comp.changeQuantity(1, true);
        expect(comp.state.ticketQuantities[1]).toBe(2);
        expect(comp.state.totalPrice).toBe(200);

        comp.changeQuantity(1, false);
        expect(comp.state.ticketQuantities[1]).toBe(1);
        expect(comp.state.totalPrice).toBe(100);

        comp.canIncreaseTicket = () => false;
        comp.changeQuantity(1, true);
        expect(comp.state.ticketQuantities[1]).toBe(1);
        expect(comp.state.totalPrice).toBe(100);
    });
});
