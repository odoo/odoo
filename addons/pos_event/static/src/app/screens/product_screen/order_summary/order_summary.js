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
            [
                ...registration.registration_answer_ids,
                ...registration.registration_answer_choice_ids,
            ].forEach((answer) => {
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
        for (const registrations of Object.values(result.byRegistration)) {
            for (const [regIdx, answers] of Object.entries(registrations)) {
                const originalReg = orderline.event_registration_ids[regIdx];
                if (!originalReg || typeof answers !== "object") {
                    continue;
                }
                const userData = {
                    name: originalReg.name,
                    email: originalReg.email,
                    phone: originalReg.phone,
                    company_name: originalReg.company_name,
                };
                for (const [questionId, answer] of Object.entries(answers)) {
                    const question = this.pos.models["event.question"].get(parseInt(questionId));
                    if (!question) {
                        continue;
                    }
                    if (question.question_type == "simple_choice") {
                        const existingChoice = originalReg.registration_answer_choice_ids.find(
                            (rec) => rec.question_id && rec.question_id.id == question.id
                        );
                        this.updateAnswer(answer, existingChoice, originalReg, question, {
                            value_answer_id: { id: parseInt(answer) },
                        });
                    } else {
                        const existing = originalReg.registration_answer_ids.find(
                            (rec) => rec.question_id && rec.question_id.id === question.id
                        );
                        if (
                            ["email", "phone", "name", "company_name"].includes(
                                question.question_type
                            )
                        ) {
                            userData[question.question_type] = answer;
                        }
                        this.updateAnswer(answer, existing, originalReg, question, {
                            value_text_box: answer,
                        });
                    }
                }
                originalReg.update(userData);
            }
        }

        // Global Question
        for (const [questionId, answer] of Object.entries(result.byOrder)) {
            const question = this.pos.models["event.question"].get(parseInt(questionId));
            if (!question) {
                continue;
            }
            for (const originalReg of orderline.event_registration_ids) {
                const userData = {
                    name: originalReg.name,
                    email: originalReg.email,
                    phone: originalReg.phone,
                    company_name: originalReg.company_name,
                };
                if (!originalReg) {
                    continue;
                }
                if (["email", "phone", "name", "company_name"].includes(question.question_type)) {
                    userData[question.question_type] = answer;
                }

                if (question.question_type === "simple_choice") {
                    const existingChoice = originalReg.registration_answer_choice_ids.find(
                        (rec) => rec.question_id && rec.question_id.id === question.id
                    );
                    this.updateAnswer(answer, existingChoice, originalReg, question, {
                        value_answer_id: { id: parseInt(answer) },
                    });
                } else {
                    const existing = originalReg.registration_answer_ids.find(
                        (rec) => rec.question_id && rec.question_id.id === question.id
                    );
                    this.updateAnswer(answer, existing, originalReg, question, {
                        value_text_box: answer,
                    });
                }
                originalReg.update(userData);
            }
        }
    },

    updateAnswer(answer, existing, originalReg, questionId, values) {
        if (answer) {
            const vals = {
                ...values,
                question_id: questionId,
                registration_id: originalReg,
            };
            existing
                ? existing.update(vals)
                : this.pos.models["event.registration.answer"].create(vals);
        } else if (existing) {
            existing.delete();
        }
    },
});
