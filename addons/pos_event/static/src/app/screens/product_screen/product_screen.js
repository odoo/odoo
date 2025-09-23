import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { patch } from "@web/core/utils/patch";
import { EventConfiguratorPopup } from "@pos_event/app/popup/event_configurator_popup/event_configurator_popup";
import { _t } from "@web/core/l10n/translation";
import { EventRegistrationPopup } from "../../popup/event_registration_popup/event_registration_popup";

patch(ProductScreen.prototype, {
    get products() {
        const products = super.products;
        return [...products].filter((p) => p.service_tracking !== "event");
    },
    getProductPrice(product) {
        if (!product.event_id) {
            return super.getProductPrice(product);
        }

        return _t("From %s", this.env.utils.formatCurrency(this.pos.getProductPrice(product)));
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

        const ticketResult = await makeAwaitable(this.dialog, EventConfiguratorPopup, {
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
                }

                return acc;
            },
            { globalSimpleChoice: {}, globalTextAnswer: {} }
        );

        for (const [ticketId, data] of Object.entries(result.byRegistration)) {
            const ticket = this.pos.models["event.event.ticket"].get(parseInt(ticketId));
            const line = await this.pos.addLineToCurrentOrder({
                product_id: ticket.product_id,
                price_unit: ticket.price,
                qty: data.length,
                event_ticket_id: ticket,
            });

            for (const registration of data) {
                const userData = {};
                for (const [questionId, answer] of Object.entries(registration)) {
                    const question = this.pos.models["event.question"].get(parseInt(questionId));

                    if (!question) {
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

                this.pos.models["event.registration"].create({
                    ...userData,
                    event_id: event,
                    event_ticket_id: ticket,
                    pos_order_line_id: line,
                    partner_id: this.pos.get_order().partner_id,
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
});
