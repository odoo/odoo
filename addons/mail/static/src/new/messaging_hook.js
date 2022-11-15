/** @odoo-module */

import { reactive, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {import("@mail/new/messaging").Messaging} Messaging
 */

/**
 *  @returns {Messaging} messaging
 */
export function useMessaging() {
    return useState(useService("mail.messaging"));
}

export function useMessageHighlight(duration = 2000) {
    let timeout;
    const state = reactive({
        async highlightMessage(msgId) {
            const lastHighlightedMessageId = state.highlightedMessageId;
            clearHighlight();
            if (lastHighlightedMessageId === msgId) {
                // Give some time for the state to update.
                await new Promise(setTimeout);
            }
            state.highlightedMessageId = msgId;
            timeout = setTimeout(clearHighlight, duration);
        },
        highlightedMessageId: null,
    });
    function clearHighlight() {
        clearTimeout(timeout);
        timeout = null;
        state.highlightedMessageId = null;
    }
    return state;
}
