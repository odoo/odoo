import { expect, test } from "@odoo/hoot";
import { EventRegistrationPopup } from "@pos_event/app/components/popup/event_registration_popup/event_registration_popup";
import { mountPosDialog, setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

async function mountPopup({ onPayload } = {}) {
    const store = await setupPosEnv();
    const event = store.models["event.event"].get(1);
    const tickets = [store.models["event.event.ticket"].get(1)];

    let payload = null;

    const comp = await mountPosDialog(EventRegistrationPopup, {
        event,
        data: [
            {
                qty: 1,
                ticket_id: tickets[0],
                product_id: tickets[0].product_id,
            },
        ],
        getPayload: (data) => {
            payload = data;
            onPayload?.(data);
        },
        close: () => {},
    });

    return { comp, event, tickets, payloadRef: () => payload };
}

test("confirm payload", async () => {
    const { comp, tickets, payloadRef } = await mountPopup();

    comp.state.byRegistration[0].questions = {
        1: "Test User",
        2: "test@test.com",
        3: "+911234567890",
        4: "1",
    };
    comp.confirm();

    const payload = payloadRef();
    const receivedValues = Object.values(payload.byRegistration[1][0]);
    expect(payload.byRegistration).toHaveLength(1);
    expect(parseInt(Object.keys(payload.byRegistration)[0])).toBe(tickets[0].id);
    expect(receivedValues).toEqual(["Test User", "test@test.com", "+911234567890", "1"]);
});

test("validateQuestion: mandatory / email / phone", async () => {
    const { comp, event } = await mountPopup();
    const mandatoryQuestion = event.question_ids.find((q) => q.is_mandatory_answer);
    const emailQuestion = event.question_ids.find((q) => q.question_type === "email");
    const phoneQuestion = event.question_ids.find((q) => q.question_type === "phone");

    expect(comp.validateQuestion(mandatoryQuestion, "")).toBe(false);
    expect(comp.validateQuestion(mandatoryQuestion, "Jethalal")).toBe(true);

    expect(comp.validateQuestion(emailQuestion, "invalid")).toBe(false);
    expect(comp.validateQuestion(emailQuestion, "jetha@gada.com")).toBe(true);

    expect(comp.validateQuestion(phoneQuestion, "123")).toBe(false);
    expect(comp.validateQuestion(phoneQuestion, "+911234567890")).toBe(true);
});

test("getValidationClass shows error only after touched", async () => {
    const { comp, event } = await mountPopup();
    const question = event.question_ids.find((q) => q.is_mandatory_answer);

    const reg0 = comp.state.byRegistration[0].questions;

    expect(comp.getValidationClass(question, reg0, 0)).toBe("");

    comp.markTouched(question.id, 0);

    expect(comp.getValidationClass(question, reg0, 0)).toBe("border border-danger");

    reg0[question.id] = "Valid value";
    expect(comp.getValidationClass(question, reg0, 0)).toBe("");
});

test("isConfirmEnabled: disabled until all required answers are valid", async () => {
    const { comp } = await mountPopup();
    const answersByType = {
        name: "Jethalal",
        email: "test@test.com",
        phone: "+911234567890",
        simple_choice: "1",
    };

    // when questions are empty
    expect(comp.isConfirmEnabled()).toBe(false);

    // Fill all questions
    for (const reg of comp.state.byRegistration) {
        for (const q of comp.questionsByRegistration) {
            reg.questions[q.id] = answersByType[q.question_type];
        }
    }
    expect(comp.isConfirmEnabled()).toBe(true);
});

test("autofill first ticket with customer data", async () => {
    const store = await setupPosEnv();
    const partner = store.models["res.partner"].get(18);
    partner.email = "john@example.com";
    partner.phone = "+1234567890";
    partner.parent_name = "Don";

    const order = store.addNewOrder();
    order.partner_id = partner;

    const event = store.models["event.event"].get(1);
    const ticket = store.models["event.event.ticket"].get(1);
    const data = [{ qty: 2, ticket_id: ticket, product_id: ticket.product_id }];

    const comp = await mountPosDialog(EventRegistrationPopup, {
        event,
        data,
        getPayload: () => {},
        close: () => {},
    });

    const [first, second] = comp.state.byRegistration.map((r) => r.questions);

    expect(Object.values(first)).toEqual([
        "Public user",
        "john@example.com",
        "+1234567890",
        "",
        "Don",
    ]);
    expect(Object.values(second)).toEqual(["", "", "", "", ""]);
});
