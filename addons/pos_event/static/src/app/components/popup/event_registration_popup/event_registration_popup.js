// Part of Odoo. See LICENSE file for full copyright and licensing details.
import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { ProductCard } from "@point_of_sale/app/components/product_card/product_card";
import { NumericInput } from "@point_of_sale/app/components/inputs/numeric_input/numeric_input";
import { useService } from "@web/core/utils/hooks";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { isValidEmail, isValidPhone } from "@point_of_sale/utils";

export class EventRegistrationPopup extends Component {
    static template = "pos_event.EventRegistrationPopup";
    static props = ["data", "getPayload", "close", "event"];
    static components = {
        Dialog,
        ProductCard,
        NumericInput,
    };
    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
        this.state = useState({
            byRegistration: [],
            byOrder: {},
            touchedFields: new Set(),
        });
        this.dataInQty = this.props.data.reduce((acc, data) => {
            for (let i = 0; i < data.qty; i++) {
                acc.push(data);
            }
            return acc;
        }, []);

        for (const [idx, data] of Object.entries(this.dataInQty)) {
            this.state.byRegistration[idx] = {
                ticket_id: data.ticket_id,
                product_id: data.product_id,
                questions: {},
            };

            for (const question of this.questionsByRegistration) {
                this.state.byRegistration[idx].questions[question.id] = "";
            }
        }

        for (const question of this.questionsOncePerOrder) {
            this.state.byOrder[question.id] = "";
        }

        // Autofill first ticket with customer data if customer is selected
        const customer = this.pos.getOrder()?.partner_id;
        if (customer && this.state.byRegistration.length) {
            const firstTicketQuestions = this.state.byRegistration[0].questions;
            const fieldMap = {
                name: customer.name,
                email: customer.email,
                phone: customer.phone,
                company_name: customer.parent_name,
            };

            this.questionsByRegistration.forEach(
                (q) =>
                    fieldMap[q.question_type] &&
                    (firstTicketQuestions[q.id] = fieldMap[q.question_type])
            );
        }

        if (this.props.event.question_ids.length === 0) {
            this.confirm();
        }
    }

    get questionsByRegistration() {
        return this.props.event.question_ids.filter((question) => !question.once_per_order);
    }

    get questionsOncePerOrder() {
        return this.props.event.question_ids.filter((question) => question.once_per_order);
    }

    getFieldKey(questionId, ticketIndex = null) {
        return ticketIndex === null ? `order:${questionId}` : `reg:${ticketIndex}:${questionId}`;
    }

    markTouched(questionId, ticketIndex = null) {
        this.state.touchedFields.add(this.getFieldKey(questionId, ticketIndex));
    }

    validateQuestion(question, value) {
        if (question.is_mandatory_answer && !value?.trim()) {
            return false;
        }
        if (!value) {
            return true;
        }
        if (question.question_type === "email") {
            return isValidEmail(value);
        }
        if (question.question_type === "phone") {
            return isValidPhone(value);
        }
        return true;
    }

    getValidationClass(question, stateObject, ticketIndex = null) {
        const value = stateObject[question.id];
        const key = this.getFieldKey(question.id, ticketIndex);

        if (this.state.touchedFields.has(key) && !this.validateQuestion(question, value)) {
            return "border border-danger";
        }
        return "";
    }

    isQuestionMissingMandatoryAnswer(id, value) {
        const question = this.pos.models["event.question"].get(id);
        return !!(question && question.is_mandatory_answer && !value);
    }

    isConfirmEnabled() {
        const areQuestionsValid = (questions, values) =>
            questions.every((q) => this.validateQuestion(q, values[q.id]));

        return (
            areQuestionsValid(this.questionsOncePerOrder, this.state.byOrder) &&
            this.state.byRegistration.every((reg) =>
                areQuestionsValid(this.questionsByRegistration, reg.questions)
            )
        );
    }

    confirm() {
        const requiredByRegistration = Object.values(this.state.byRegistration).some((data) => {
            for (const [id, value] of Object.entries(data.questions)) {
                if (this.isQuestionMissingMandatoryAnswer(id, value)) {
                    return true;
                }
            }
        });

        const requiredByOrder = Object.entries(this.state.byOrder).some(([id, value]) =>
            this.isQuestionMissingMandatoryAnswer(id, value)
        );

        if (requiredByRegistration || requiredByOrder) {
            this.dialog.add(AlertDialog, {
                title: "Oh snap !",
                body: "Please fill in all required fields",
            });
            return;
        }

        const registrationByTickets = this.state.byRegistration.reduce((acc, data) => {
            if (!acc[data.ticket_id.id]) {
                acc[data.ticket_id.id] = [];
            }

            acc[data.ticket_id.id].push(data.questions);
            return acc;
        }, {});

        this.props.getPayload({
            byRegistration: registrationByTickets,
            byOrder: this.state.byOrder,
        });
        this.props.close();
    }
    close() {
        this.props.close();
    }
}
