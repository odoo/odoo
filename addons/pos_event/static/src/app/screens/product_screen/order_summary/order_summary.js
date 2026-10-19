import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { patch } from "@web/core/utils/patch";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { EventRegistrationPopup } from "@pos_event/app/components/popup/event_registration_popup/event_registration_popup";

patch(OrderSummary.prototype, {
    async onOrderlineLongPress(ev, orderline) {
        if (!orderline.event_ticket_id) {
            return super.onOrderlineLongPress(ev, orderline);
        }
        const event = orderline.event_ticket_id.event_id;
        const registrationJson = {};
        orderline.event_registration_ids.forEach((registration, index) => {
            const answers = {};
            registration.registration_answer_ids.forEach((answer) => {
                answers[answer.question_id.id] =
                    answer.value_text_box ?? answer.value_answer_id?.id;
            });
            registrationJson[index] = answers;
        });

        const result = await makeAwaitable(this.dialog, EventRegistrationPopup, {
            event,
            data: [
                {
                    product_id: orderline.product_id,
                    qty: orderline.qty,
                    ticket_id: orderline.event_ticket_id,
                    registration_ids: registrationJson,
                },
            ],
        });

        if (result) {
            this._processEventRegistrationResult(result, orderline);
        }
    },

    _processEventRegistrationResult(result, orderline) {
        const questionModel = this.pos.models["event.question"];

        const processAnswer = (eventReg, questionId, answer) => {
            const question = questionModel.get(Number(questionId));
            if (!question) {
                return;
            }
            const eventRegAnswerData = eventReg.registration_answer_ids.find(
                (rec) => rec.question_id && rec.question_id.id === question.id
            );
            let values =
                question.question_type === "simple_choice"
                    ? { value_answer_id: { id: Number(answer) } }
                    : { value_text_box: answer };
            if (!eventRegAnswerData) {
                values = {
                    ...values,
                    question_id: question.id,
                    registration_id: eventReg,
                };
            }
            this.updateAnswer(answer, eventRegAnswerData, values);

            const eventRegistrationField = ["email", "phone", "name", "company_name"].includes(
                question.question_type
            );
            return eventRegistrationField ? { [question.question_type]: answer } : {};
        };
        const applyAnswersToRegistration = (eventReg, answers) => {
            if (!eventReg || typeof answers !== "object") {
                return;
            }
            // existing values
            const existingAnswerObj = {};
            eventReg.registration_answer_ids.forEach((answer) => {
                existingAnswerObj[answer.question_id.id] =
                    answer.value_text_box ?? answer.value_answer_id?.id ?? null;
            });
            const eventRegistrationData = {};
            for (const [questionId, answer] of Object.entries(answers)) {
                const existingAnswer = existingAnswerObj[questionId] ?? "";
                // Update only those questions for which the answer has been modified
                if (existingAnswer !== answer) {
                    const updatedField = processAnswer(eventReg, questionId, answer);
                    if (updatedField) {
                        Object.assign(eventRegistrationData, updatedField);
                    }
                }
            }
            eventReg.update(eventRegistrationData);
        };
        // Registration Specific Questions
        for (const registrations of Object.values(result.byRegistration)) {
            for (const [regIdx, answers] of Object.entries(registrations)) {
                const eventReg = orderline.event_registration_ids[regIdx];
                applyAnswersToRegistration(eventReg, answers);
            }
        }
        // Global Questions
        for (const eventReg of orderline.event_registration_ids) {
            applyAnswersToRegistration(eventReg, result.byOrder);
        }
    },

    updateAnswer(updatedAnswer, eventRegAnswerData, values) {
        if (updatedAnswer) {
            eventRegAnswerData
                ? eventRegAnswerData.update(values)
                : this.pos.models["event.registration.answer"].create(values);
        } else if (eventRegAnswerData) {
            eventRegAnswerData.delete();
        }
    },
});
