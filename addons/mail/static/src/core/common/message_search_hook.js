import { useSequential } from "@mail/utils/common/hooks";
import { createDocumentFragmentFromContent } from "@mail/utils/common/html";
import { useState, onWillUnmount, markup } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { escapeRegExp } from "@web/core/utils/strings";

export const HIGHLIGHT_CLASS = "o-mail-Message-searchHighlight";

/**
 * @param {string} searchTerm
 * @param {string} target
 */
export function searchHighlight(searchTerm, target) {
    if (!searchTerm) {
        return target;
    }
    const htmlDoc = createDocumentFragmentFromContent(target);
    for (const term of searchTerm.split(" ")) {
        const regexp = new RegExp(`(${escapeRegExp(term)})`, "gi");
        // Special handling for '
        // Note: browsers use XPath 1.0, so uses concat() rather than ||
        const split = term.toLowerCase().split("'");
        let lowercase = split.map((s) => `'${s}'`).join(', "\'", ');
        let uppercase = lowercase.toUpperCase();
        if (split.length > 1) {
            lowercase = `concat(${lowercase})`;
            uppercase = `concat(${uppercase})`;
        }
        const matchs = htmlDoc.evaluate(
            `//*[text()[contains(translate(., ${uppercase}, ${lowercase}), ${lowercase})]]`, // Equivalent to `.toLowerCase()` on all searched chars
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

/** @param {import('models').Thread} thread */
export function useMessageSearch(thread) {
    const store = useService("mail.store");
    const sequential = useSequential();
    const state = useState({
        thread,
        async search(before = false) {
            if (this.searchTerm) {
                this.searching = true;
                const data = await sequential(() =>
                    store.search(this.searchTerm, this.thread, before)
                );
                if (!data) {
                    return;
                }
                const { count, loadMore, messages } = data;
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
