// Part of Odoo. See LICENSE file for full copyright and licensing details.
export function increaseQuantityOfTicket(ticket) {
    return [
        {
            content: `increase quantity`,
            trigger: `.modal .o_event_configurator_popup div:contains('${ticket}') .fa.fa-plus`,
            run: "click",
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

export function answerTicketQuestion(ticketNumber, question, answer) {
    return [
        {
            content: `Answer question ${question} with ${answer} for ticket ${ticketNumber}`,
            trigger: `.ticket_question:contains('Ticket #${ticketNumber}') .input-group:contains('${question}') input`,
            run: `edit ${answer}`,
        },
    ];
}

export function answerGlobalTextQuestion(question, answer) {
    return [
        {
            content: `Answer question ${question} with ${answer} for global`,
            trigger: `.global_question:contains('${question}') input`,
            run: `edit ${answer}`,
        },
    ];
}
