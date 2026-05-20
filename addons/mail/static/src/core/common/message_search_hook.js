import { useState } from "@web/owl2/utils";
import { SearchState } from "@mail/utils/common/hooks";
import { getInnerHtml } from "@mail/utils/common/html";
import { effect, onMounted, onWillDestroy, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { createDocumentFragmentFromContent } from "@web/core/utils/html";
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
    return getInnerHtml(htmlDoc.body);
}

export class MessageSearchState extends SearchState {
    count = 0;
    /** @type {boolean | undefined} */
    is_notification = undefined;
    hasMore = false;
    /** @type {import('@mail/core/common/message_model').Message[]} */
    messages = [];
    searched = false;
    /** @type {import('models').Thread | undefined} */
    thread;
    loadMoreBeforeMessageId;
    /** @type {import("models").Store} */
    store;

    /** @param {import('models').Thread} [initialThread] */
    constructor(initialThread) {
        super();
        this.store = useService("mail.store");
        this.thread = initialThread;
        this.fetch = this.fetchMessages.bind(this);
        let disposeEffect = () => {};
        onMounted(() => {
            disposeEffect = effect(() => {
                if (this.isActive) {
                    this.run();
                } else if (this.searched) {
                    this.clear();
                }
            });
        });
        onWillDestroy(disposeEffect);
        onWillUnmount(() => this.clear());
    }

    get isActive() {
        return !!this.searchTerm || this.is_notification !== undefined;
    }

    get deps() {
        return [this.is_notification];
    }

    /** @param {string} term */
    async fetchMessages(term) {
        const before = this.loadMoreBeforeMessageId;
        this.loadMoreBeforeMessageId = undefined;
        const data = await this.store.searchMessagesInThread(
            term,
            this.thread,
            before ?? false,
            this.is_notification
        );
        if (!data) {
            return;
        }
        this.searched = true;
        this.count = data.count;
        this.hasMore = data.loadMore;
        if (before !== undefined) {
            this.messages.push(...data.messages);
        } else {
            this.messages = data.messages;
            if (data.messages.length === 0) {
                return false;
            }
        }
    }

    /** @param {number} beforeMessageId */
    loadMore(beforeMessageId) {
        this.loadMoreBeforeMessageId = beforeMessageId;
        this.run();
    }

    clear() {
        this.is_notification = undefined;
        this.messages = [];
        this.searched = false;
        this.count = 0;
        this.hasMore = false;
        this.reset();
    }

    /**
     * Highlights `searchTerm` in `text`.
     * @param {string} text
     */
    highlight(text) {
        return searchHighlight(this.searchTerm, text);
    }
}

/**
 * @param {import('models').Thread} [initialThread]
 * @returns {MessageSearchState}
 */
export function useMessageSearch(initialThread) {
    return useState(new MessageSearchState(initialThread));
}
