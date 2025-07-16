import { Component, useState, useRef } from "@odoo/owl";
import { Stepper } from "@pos_self_order/app/components/combo_stepper/combo_stepper";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { useScrollShadow } from "@pos_self_order/app/utils/scroll_shadow_hook";
import { isValidEmail } from "@point_of_sale/utils";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { useStickyTitleObserver } from "@pos_self_order/app/utils/sticky_title_observer";

export class EventPage extends Component {
    static template = "pos_self_order_event.EventPage";
    static props = ["eventTemplate"];
    static components = { Stepper };

    setup() {
        this.selfOrder = useSelfOrder();
        this.router = useService("router");
        this.notification = useService("notification");
        this.event = this.props.eventTemplate;

        this.state = useState({
            qty: 1,
            showStickyTitle: false,
            selectedStep: this.steps[0],
            ticketQuantities: {},
            globalAnswers: {},
            ticketDetails: {},
            totalPrice: 0,
            selectedSlot: null,
            slotTicketAvailabilities: {},
            touchedFields: new Set(),
        });

        this.eventNameRef = useRef("eventName");
        this.scrollContainerRef = useRef("scrollContainer");
        this.scrollShadow = useScrollShadow(this.scrollContainerRef);
        useStickyTitleObserver("eventName", (isSticky) => (this.state.showStickyTitle = isSticky));
    }

    get eventTickets() {
        return this.event.event_ticket_ids;
    }
    eventQuestions() {
        return {
            all: this.event.question_ids,
            global: this.event.question_ids.filter((q) => q.once_per_order),
            ticket: this.event.question_ids.filter((q) => !q.once_per_order),
        };
    }
    get steps() {
        const steps = [
            ...(this.event?.event_slot_ids.length
                ? [{ id: "slot", name: _t("Slot Selection") }]
                : []),
            { id: "ticket", name: _t("Ticket selection") },
            { id: "info", name: _t("Fill information") },
        ];
        return steps;
    }
    get ticketForms() {
        return this.eventTickets.flatMap((ticket) => {
            const qty = this.state.ticketQuantities[ticket.id] || 0;
            return Array.from({ length: qty }, (_, i) => ({
                ticketId: ticket.id,
                ticketName: ticket.name,
                index: i + 1,
            }));
        });
    }
    isBackVisible() {
        return this.state.selectedStep.id !== this.steps[0].id;
    }
    isTextInput(question) {
        return ["text_box", "name", "email", "phone", "company_name"].includes(
            question.question_type
        );
    }
    isUserDataFields(question) {
        return ["name", "email", "phone", "company_name"].includes(question.question_type);
    }
    getInputProps(question) {
        const inputTypes = {
            text_box: { type: "text", placeholder: "" },
            name: { type: "text", placeholder: "Full Name" },
            email: { type: "email", placeholder: "Email" },
            phone: { type: "tel", placeholder: "Phone" },
            company_name: { type: "text", placeholder: "Company Name" },
        };
        return inputTypes[question.question_type] || { type: "text", placeholder: "" };
    }

    isValidPhone(value) {
        return !!value && /^\+?[()\d\s-.]{8,18}$/.test(value);
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
            return this.isValidPhone(value);
        }
        return true;
    }

    validateAnswers() {
        const { global, ticket = [] } = this.eventQuestions();
        if (global.some((q) => !this.validateQuestion(q, this.state.globalAnswers[q.id]))) {
            return false;
        }
        return !this.ticketForms.some((form) => {
            const answers = this.state.ticketDetails[`${form.ticketId}_${form.index}`] || {};
            return ticket.some((q) => !this.validateQuestion(q, answers[q.id]?.value));
        });
    }

    markTouched(key) {
        this.state.touchedFields.add(key);
    }

    getFieldKey(question, form) {
        if (form?.ticketId) {
            return `${form.ticketId}_${form.index}_${question.id}`;
        }
        return question.id;
    }

    getFieldErrorClass(question, form) {
        const key = this.getFieldKey(question, form);
        const value = form?.ticketId
            ? this.state.ticketDetails?.[`${form.ticketId}_${form.index}`]?.[question.id]?.value
            : this.state.globalAnswers?.[question.id];

        if (this.state.touchedFields.has(key) && !this.validateQuestion(question, value)) {
            return "border border-danger";
        }
        return "";
    }

    slotAvailabilityText(slot) {
        if (slot.seats_available > 0) {
            return slot.seats_available + _t(" seats available");
        }
        if (slot.seats_available === 0 && !this.event.seats_limited) {
            return _t("Unlimited Seats");
        }
        return _t("No seats available");
    }

    seatAvailability(ticket) {
        if (this.event.is_multi_slots && this.state.selectedSlot) {
            const slotId = this.state.selectedSlot;
            return Boolean(this.state.slotTicketAvailabilities?.[ticket.id]?.[slotId] ?? 0);
        }
        if (this.event.seats_limited && !this.event.seats_available) {
            return false;
        }
        return Boolean(ticket.seats_available) || ticket.seats_max === 0;
    }

    changeQuantity(ticketId, increase) {
        const ticket = this.selfOrder.models["event.event.ticket"].get(ticketId);
        if (!ticket || !this.event) {
            return;
        }

        const current = this.state.ticketQuantities[ticketId] || 0;
        const newQty = Math.max(0, current + (increase ? 1 : -1));

        if (increase && !this.canIncreaseTicket(ticket, this.event, newQty)) {
            return;
        }

        if (newQty) {
            this.state.ticketQuantities[ticketId] = newQty;
        } else {
            delete this.state.ticketQuantities[ticketId];
        }

        this.state.totalPrice = this.eventTickets.reduce(
            (sum, ticket) =>
                sum + (ticket.price || 0) * (this.state.ticketQuantities[ticket.id] || 0),
            0
        );
    }

    canIncreaseTicket(ticket, event, newQty) {
        if (event.is_multi_slots && this.state.selectedSlot) {
            // When the event has multiple slots, check both slot-level and ticket-level limits:
            // - If newQty exceeds the slot's available seats, OR
            // - If newQty exceeds the ticket's available seats for that slot
            const slotId = this.state.selectedSlot;
            const slotTicketAvailable = this.state.slotTicketAvailabilities?.[ticket.id]?.[slotId];
            const slotRemaining =
                this.state.slotTicketAvailabilities?.[
                    Object.keys(this.state.slotTicketAvailabilities)[0]
                ]?.[slotId];
            const totalSelectedOther = Object.entries(this.state.ticketQuantities).reduce(
                (sum, [id, qty]) => sum + (Number(id) === ticket.id ? 0 : qty),
                0
            );
            if (newQty > slotRemaining - totalSelectedOther) {
                this.notifyLimit(slotRemaining, "slot");
                return false;
            }
            if (slotTicketAvailable !== "unlimited" && newQty > slotTicketAvailable) {
                this.notifyLimit(slotTicketAvailable, "ticket");
                return false;
            }
            return true;
        }
        // For events without slots, check both event-level and ticket-level limits:
        // - If newQty exceeds the ticket’s available seats
        // - If newQty exceeds the total event’s available seats
        const ticketLimit =
            ticket.seats_max === 0 && ticket.seats_available === 0
                ? Number.MAX_SAFE_INTEGER
                : ticket.seats_available || 0;
        if (newQty > ticketLimit) {
            this.notifyLimit(ticketLimit, "ticket");
            return false;
        }
        const totalEventLimit = event.seats_limited
            ? Math.min(event.seats_available || 0, this.eventTotalSeats(event))
            : this.eventTotalSeats(event);
        const totalSelectedOther = Object.entries(this.state.ticketQuantities).reduce(
            (sum, [id, qty]) => sum + (Number(id) === ticket.id ? 0 : qty),
            0
        );
        const remaining = totalEventLimit - totalSelectedOther;
        if (newQty > remaining) {
            this.notifyLimit(remaining, "event");
            return false;
        }
        return true;
    }

    eventTotalSeats(event) {
        return event.event_ticket_ids.some(
            (ticket) => ticket.seats_max === 0 && ticket.seats_available === 0
        )
            ? Number.MAX_SAFE_INTEGER
            : event.event_ticket_ids.reduce(
                  (sum, ticket) => sum + (ticket.seats_available || 0),
                  0
              );
    }

    notifyLimit(limit, type) {
        this.notification.add(
            !limit
                ? _t("No seats available for %s", type)
                : _t("Only %s seats available for %s", limit, type),
            { type: "danger" }
        );
    }

    isNextEnabled() {
        const step = this.state.selectedStep.id;
        if (step === "slot") {
            return !!this.state.selectedSlot;
        }
        if (step === "ticket") {
            return Object.values(this.state.ticketQuantities).some((quantity) => quantity > 0);
        }
        if (step === "info") {
            return this.validateAnswers();
        }
        return false;
    }

    onStepClicked(stepIdx) {
        const step = this.steps[stepIdx];
        if (["ticket", "info"].includes(step.id) && !this.isNextEnabled()) {
            return;
        }
        this.state.selectedStep = step;
    }

    next() {
        const idx = this.steps.findIndex((s) => s.id === this.state.selectedStep.id);
        if (this.isNextEnabled() && idx < this.steps.length - 1) {
            this.state.selectedStep = this.steps[idx + 1];
        }
    }
    back() {
        const idx = this.steps.findIndex((s) => s.id === this.state.selectedStep.id);
        if (idx > 0) {
            this.state.selectedStep = this.steps[idx - 1];
        } else {
            this.goBack();
        }
    }

    selectSlot(slot) {
        if (slot.seats_available <= 0 && this.event.seats_limited) {
            this.state.selectedSlot = null;
            this.state.slotTicketAvailabilities = {};
            return;
        }
        this.state.selectedSlot = slot.id;
        this.state.ticketQuantities = {};
        this.fetchSlotAvaiblity(slot);
    }

    async fetchSlotAvaiblity(slot) {
        const slotTickets = this.event.event_ticket_ids.map((t) => [slot.id, t.id]);
        const slotTicketAvailabilities = await rpc("/pos-self-order/get-slot-availability", {
            access_token: this.selfOrder.access_token,
            event_id: this.event.id,
            slot_tickets: slotTickets,
        });

        const avaibilityByTicket = slotTicketAvailabilities.reduce((acc, availability, idx) => {
            const slotId = slotTickets[idx][0];
            const ticketId = slotTickets[idx][1] ?? idx;

            if (!acc[ticketId]) {
                acc[ticketId] = {};
            }
            acc[ticketId][slotId] = availability === null ? "unlimited" : availability || 0;

            return acc;
        }, {});
        this.state.slotTicketAvailabilities = avaibilityByTicket;
    }

    updateTicketDetail(ticketId, index, questionId, title, value) {
        const key = `${ticketId}_${index}`;
        this.state.ticketDetails = {
            ...this.state.ticketDetails,
            [key]: {
                ...(this.state.ticketDetails[key] || {}),
                [questionId]: { title, value },
            },
        };
    }

    updateGlobalAnswer(questionId, value) {
        this.state.globalAnswers[questionId] = value;
    }

    async addToCart() {
        if (!this.validateAnswers()) {
            return this.notification.add(_t("Please fill in all required fields"), {
                type: "danger",
            });
        }

        const tickets = this.event.event_ticket_ids.filter(
            (t) => t.product_id?.service_tracking === "event"
        );

        for (const [ticketId, qty] of Object.entries(this.state.ticketQuantities)) {
            if (qty <= 0) {
                continue;
            }
            const ticket = tickets.find((t) => t.id === parseInt(ticketId));
            if (!ticket) {
                continue;
            }

            const line = await this.selfOrder.addToCart(
                ticket.product_id.product_tmpl_id,
                qty,
                "",
                {},
                {
                    event_price: ticket.price,
                    event_ticket_id: ticket.id,
                }
            );

            this.createRegistrations(ticket, qty, line);
        }

        this.goBack();
    }

    createRegistrations(ticket, qty, line) {
        for (let i = 1; i <= qty; i++) {
            const details = this.state.ticketDetails[`${ticket.id}_${i}`] || {};
            const mergedDetails = {
                ...Object.fromEntries(
                    Object.entries(this.state.globalAnswers).map(([questionId, value]) => [
                        questionId,
                        { value },
                    ])
                ),
                ...details,
            };
            const { userData, simpleChoice, textAnswer } = this.extractAnswers(mergedDetails);

            this.selfOrder.models["event.registration"].create({
                ...userData,
                event_id: this.event.id,
                event_ticket_id: ticket,
                event_slot_id: this.event.is_multi_slots ? this.state.selectedSlot : null,
                pos_order_line_id: line,
                partner_id: this.selfOrder.currentOrder.partner_id,
                registration_answer_ids: this.formatTextAnswers(textAnswer),
                registration_answer_choice_ids: this.formatChoiceAnswers(simpleChoice),
            });
        }
    }

    extractAnswers(details) {
        const userData = {};
        const simpleChoice = {};
        const textAnswer = {};

        for (const [questionId, { value }] of Object.entries(details)) {
            const question = this.selfOrder.models["event.question"].get(parseInt(questionId));
            if (!question) {
                continue;
            }
            if (this.isUserDataFields(question)) {
                userData[question.question_type] = value;
            }
            if (question.question_type === "simple_choice") {
                simpleChoice[questionId] = value;
            }
            if (value) {
                textAnswer[questionId] = value;
            }
        }
        return { userData, simpleChoice, textAnswer };
    }

    formatTextAnswers(textAnswer) {
        return Object.entries(textAnswer).map(([questionId, answer]) => [
            "create",
            {
                question_id: this.selfOrder.models["event.question"].get(parseInt(questionId)),
                value_text_box: answer,
            },
        ]);
    }
    formatChoiceAnswers(simpleChoice) {
        return Object.entries(simpleChoice).map(([questionId, answer]) => [
            "create",
            {
                question_id: this.selfOrder.models["event.question"].get(parseInt(questionId)),
                value_answer_id: this.selfOrder.models["event.question.answer"].get(
                    parseInt(answer)
                ),
            },
        ]);
    }

    goBack() {
        this.router.navigate("product_list");
    }
}
