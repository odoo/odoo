export function updateSeats(models, data) {
    for (const ev of data) {
        const event = models["event.event"].get(ev.event_id);
        if (!event) {
            continue;
        }

        event.seats_available = ev.seats_available;

        for (const ticket of ev.event_ticket_ids) {
            const eventTicket = models["event.event.ticket"].get(ticket.ticket_id);
            if (eventTicket) {
                eventTicket.seats_available = ticket.seats_available;
            }
        }

        for (const slot of ev.event_slot_ids) {
            const eventSlot = models["event.slot"].get(slot.slot_id);
            if (eventSlot) {
                eventSlot.seats_available = slot.seats_available;
            }
        }
    }
}

export function createDummyProductForEvents(models) {
    const eventProducts = [];
    for (const event of models["event.event"].getAll()) {
        const eventTicketWithProduct = event.event_ticket_ids.filter((ticket) => ticket.product_id);
        if (!eventTicketWithProduct.length) {
            continue;
        }

        const categIds = eventTicketWithProduct.flatMap(
            (ticket) => ticket.product_id.pos_categ_ids
        );
        const taxeIds = eventTicketWithProduct.flatMap((ticket) => ticket.product_id.taxes_id);

        const product = models["product.template"].create({
            id: `dummy_${event.id}`,
            available_in_pos: true,
            display_name: event.name,
            name: event.name,
            pos_categ_ids: categIds.map((categ) => ["link", categ]),
            taxes_id: taxeIds.map((tax) => ["link", tax]),
            _event_id: event.id,
        });

        // Disable original ticket products
        for (const ticket of event.event_ticket_ids) {
            const productTmpl = ticket.product_id?.product_tmpl_id;
            if (productTmpl) {
                productTmpl.available_in_pos = false;
            }
        }
        eventProducts.push(product);
    }
    return eventProducts;
}

export function createRegistrationAnswer(models, textAnswers) {
    return textAnswers.reduce(
        (acc, [questionId, answer]) => {
            const question = models["event.question"].get(parseInt(questionId));
            const answers = question?.question_type === "checkbox" ? answer : [answer];
            answers.forEach((ans) => {
                const ansId = models["event.question.answer"].get(parseInt(ans));
                acc.push([
                    "create",
                    {
                        question_id: question,
                        ...(ansId ? { value_answer_id: ansId } : { value_text_box: ans }),
                    },
                ]);
            })
        return acc
    }, []);
}

export function extractRegistrationData(models, questions, userData = {}) {
    const IDENTIFICATION_QUESTION_TYPES = new Set(["name", "email", "phone", "company_name"]);

    return Object.entries(questions).reduce(
        (acc, [qId, answer]) => {
            if (!answer) {
                return acc;
            }

            const question = models["event.question"].get(parseInt(qId));
            if (!question) {
                return acc;
            }

            if (question.question_type === "checkbox") {
                acc.textAnswer[qId] = [];
                for (const [answerId, isChecked] of Object.entries(answer)) {
                    if (
                        isChecked &&
                        models["event.question.answer"].get(parseInt(answerId))
                    ) {
                        acc.textAnswer[qId].push(answerId);
                    }
                }
            } else {
                acc.textAnswer[qId] = answer;
                if (IDENTIFICATION_QUESTION_TYPES.has(question.question_type)) {
                    userData[question.question_type] ??= answer;
                }
            }

            return acc;
        },
        { textAnswer: {}, userData }
    );
}
