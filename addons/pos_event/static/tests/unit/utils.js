import { patch } from "@web/core/utils/patch";
import * as awaitableDialogUtil from "@point_of_sale/app/utils/make_awaitable_dialog";

patch(awaitableDialogUtil, {
    async makeAwaitable(dialog, comp, props, options) {
        const { name: compName } = comp;
        if (compName == "EventSlotSelectionPopup") {
            return { slotId: parseInt(Object.keys(props.availabilityPerSlot)[0]) };
        }
        if (compName == "EventConfiguratorPopup") {
            return props.tickets.map((ticket) => ({
                qty: 1,
                product_id: ticket.product_id,
                ticket_id: ticket,
            }));
        }
        if (compName == "EventRegistrationPopup") {
            const getQuestionRes = (question) => {
                const answers = {
                    name: "Test User",
                    email: "test@test.com",
                    phone: "+911234567890",
                    simple_choice: question.answer_ids?.[0]?.id.toString(),
                };
                return [question.id, answers[question.question_type] || ""];
            };
            return {
                byRegistration: Object.fromEntries(
                    props.event.event_ticket_ids.map((ticket) => [
                        ticket.id,
                        [
                            Object.fromEntries(
                                ticket.event_id.question_ids.map((que) => getQuestionRes(que))
                            ),
                        ],
                    ])
                ),
                byOrder: {},
            };
        }
        return super.makeAwaitable(...arguments);
    },
});
