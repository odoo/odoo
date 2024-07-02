// Part of Odoo. See LICENSE file for full copyright and licensing details.
export function increaseQuantityOfTicket(ticket) {
    return [
        {
            content: `increase quantity`,
            trigger: `.o_event_configurator_popup div:contains('${ticket}') .fa.fa-plus`,
            run: "click",
            in_modal: true,
        },
    ];
}

export function decreaseQuantityOfTicket(ticket) {
    return [
        {
            content: `decrease quantity`,
            trigger: `.o_event_configurator_popup div:contains('${ticket}') .fa.fa-minus`,
            run: "click",
            in_modal: true,
        },
    ];
}

export function answerTicketSelectQuestion(ticketNumber, question, answer) {
    return [
        {
            content: `Answer question ${question} with ${answer} for ticket ${ticketNumber}`,
            trigger: `.ticket_question:contains('Ticket #${ticketNumber}') .input-group:contains('${question}') select`,
            run: `selectByLabel ${answer}`,
        },
    ];
}

export function answerGlobalSelectQuestion(question, answer) {
    return [
        {
            content: `Answer question ${question} with ${answer} for global`,
            trigger: `.global_question:contains('${question}') select`,
            run: `selectByLabel ${answer}`,
        },
    ];
}

export function pickTicket(name) {
    return [
        {
            content: `pick ticket with name: ${name}`,
            trigger: `.o-event-ticket:contains('${name}')`,
            in_modal: true,
            run: "click",
        },
    ];
}

export function printTicket(mode) {
    return [
        {
            content: `print ticket with mode: ${mode}`,
            trigger: `.o-event-button .o-event-${mode}`,
            run: "click",
        },
    ];
}

export function eventRemainingSeat(name, seats) {
    return [
        {
            content: `check remaining seats for ${name}`,
            trigger: `article:contains('${name}'):contains('${seats} left')`,
            run: "click",
        },
    ];
}
