/* @odoo-module */

import { useSequential } from "@mail/utils/common/hooks";
import { useState, onWillUnmount, markup } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export const HIGHLIGHT_CLASS = "o-mail-Message-searchHighlight";

/**
 * @param {string} searchTerm
 * @param {string} target
 */
export function searchHighlight(searchTerm, target) {
    if (!searchTerm) {
        return target;
    }
    const htmlDoc = new DOMParser().parseFromString(target, "text/html");
    for (const term of searchTerm.split(" ")) {
        const regexp = new RegExp(`(${term})`, "gi");
        const matchs = htmlDoc.evaluate(
            `//*[text()[contains(translate(., '${term.toUpperCase()}', '${term.toLowerCase()}'), '${term.toLowerCase()}')]]`,
            htmlDoc,
            null,
            XPathResult.ORDERED_NODE_SNAPSHOT_TYPE
        );
        for (let i = 0; i < matchs.snapshotLength; i++) {
            const element = matchs.snapshotItem(i);
            const newNode = [];
            for (const node of element.childNodes) {
                const match = node.textContent.match(regexp);
                if (node.nodeType === Node.TEXT_NODE && match?.length > 0) {
                    let curIndex = 0;
                    for (const match of node.textContent.matchAll(regexp)) {
                        const start = htmlDoc.createTextNode(
                            node.textContent.slice(curIndex, match.index)
                        );
                        newNode.push(start);
                        const span = htmlDoc.createElement("span");
                        span.setAttribute("class", HIGHLIGHT_CLASS);
                        span.textContent = match[0];
                        newNode.push(span);
                        curIndex = match.index + match[0].length;
                    }
                    const end = htmlDoc.createTextNode(node.textContent.slice(curIndex));
                    newNode.push(end);
                } else {
                    newNode.push(node);
                }
            }
            element.replaceChildren(...newNode);
        }
    }
    return markup(htmlDoc.body.innerHTML);
}

/** @param {import('@mail/core/common/thread_model').Thread} thread */
export function useMessageSearch(thread) {
    const threadService = useService("mail.thread");
    const sequential = useSequential();
    const state = useState({
        thread,
        async search(before = false) {
            if (this.searchTerm) {
                this.searching = true;
                const { count, loadMore, messages } = await sequential(() =>
                    threadService.search(this.searchTerm, this.thread, before)
                );
                this.searched = true;
                this.searching = false;
                this.count = count;
                this.loadMore = loadMore;
                if (before) {
                    this.messages.push(...messages);
                } else {
                    this.messages = messages;
                }
            } else {
                this.clear();
            }
        },
        count: 0,
        clear() {
            this.messages = [];
            this.searched = false;
            this.searching = false;
            this.searchTerm = undefined;
        },
        loadMore: false,
        /** @type {import('@mail/core/common/message_model').Message[]} */
        messages: [],
        /** @type {string|undefined} */
        searchTerm: undefined,
        searched: false,
        searching: false,
        /** @param {string} target */
        highlight: (target) => searchHighlight(state.searchTerm, target),
    });
    onWillUnmount(() => {
        state.clear();
    });
    return state;
}
