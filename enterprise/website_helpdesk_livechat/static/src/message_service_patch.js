/* @odoo-module */

import { Message } from "@mail/core/common/message";
import { markup } from "@odoo/owl";

import { patch } from "@web/core/utils/patch";

function addNewTicketsToMessage(oldMessage, newElement) {
    const parsedDoc = new DOMParser().parseFromString(oldMessage,'text/html');

    const loadMoreDiv = parsedDoc.querySelector('.o_load_more');
    if (loadMoreDiv) {
        loadMoreDiv.parentElement.removeChild(loadMoreDiv);
    }

    const tempContainer = parsedDoc.createElement('div');
    tempContainer.innerHTML = newElement;

    const bodyElement = parsedDoc.querySelector('.o_mail_notification');
    while (tempContainer.firstChild) {
        bodyElement.appendChild(tempContainer.firstChild);
    }
    return markup(parsedDoc.documentElement.outerHTML);
}

patch(Message.prototype, {
    async loadMoreTickets(message, listKeywords, loadCounter) {
        const ticketsHTML = await this.env.services.orm.call(
            "discuss.channel",
            "fetch_ticket_by_keyword",
            [this.props.message.resId],
            {
                list_keywords: listKeywords.split(" "),
                load_counter: parseInt(loadCounter),
            }
        );

        message.body = addNewTicketsToMessage(message.body, ticketsHTML);
    },
    onClick(ev) {
        const { oeLst, oeLoadCounter, oeType } = ev.target.dataset;
        if (oeType == "load") {
            this.loadMoreTickets(this.props.message, oeLst, oeLoadCounter);
            return;
        }
        super.onClick(ev);
    },
});
