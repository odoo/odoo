// Part of Odoo. See LICENSE file for full copyright and licensing details.
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";

export function SettleEventRegistration(n = 1) {
    return [
        ...ProductScreen.clickControlButton("Quotation / Order"),
        {
            content: `select nth order`,
            trigger: `.modal:not(.o_inactive_modal) table.o_list_table tbody tr.o_data_row:nth-child(${n}) td`,
            run: "click",
        },
        {
            content: `Choose to settle the order`,
            trigger: `.modal:not(.o_inactive_modal) .selection-item:contains('Settle the order')`,
            run: "click",
        },
    ];
}

export function increaseQuantityOfTicket(ticket) {
    return [
        {
            content: `increase quantity`,
            trigger: `.modal .o_event_configurator_popup div:contains('${ticket}') [data-icon="add"]`,
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
