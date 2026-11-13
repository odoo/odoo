import { StorePlugin } from "@mail/core/common/store_plugin";
import { Thread } from "@mail/core/common/thread_model";
import { useMaybePlugin } from "@mail/utils/common/hooks";
import { getInnerHtml } from "@mail/utils/common/html";
import { SearchStatePlugin } from "@mail/utils/common/search_state_plugin";

import { computed, signal, t, useConfig, usePlugin } from "@odoo/owl";

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
    const validTerms = searchTerm.split(" ").filter(Boolean);
    if (!validTerms.length) {
        return target;
    }
    const htmlDoc = createDocumentFragmentFromContent(target);
    for (const term of validTerms) {
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

/**
 * Returns a function highlighting the term of the surrounding message search,
 * if any, in the given text.
 *
 * @returns {(text: string) => string}
 */
export function useSearchHighlight() {
    const messageSearch = useMaybePlugin(MessageSearchPlugin);
    return (text) => searchHighlight(messageSearch?.searchTerm(), text);
}

/**
 * Searches messages in a thread by term and message type.
 * Config:
 * - `thread`: function returning the thread to search.
 */
export class MessageSearchPlugin extends SearchStatePlugin {
    /** @type {import("@odoo/owl").Signal<number>} */
    count = signal(0);
    deps = computed(() => [this.searchFilter()]);
    fetch = this.fetchMessages.bind(this);
    /** @type {import("@odoo/owl").Signal<boolean>} */
    hasMore = signal(false);
    isActive = computed(() => !!this.searchTerm() || this.searchFilter() !== undefined);
    loadMoreBeforeMessageId;
    /** @type {import("@odoo/owl").Signal<import("@mail/core/common/message_model").Message[]>} */
    messages = signal([]);
    /** @type {import("@odoo/owl").Signal<boolean>} */
    searched = signal(false);
    /** @type {import("@odoo/owl").Signal<string | undefined>} */
    searchFilter = signal(undefined);
    searchId = 0;
    store = usePlugin(StorePlugin);
    thread = useConfig("thread", t.function([], t.instanceOf(Thread).optional()));

    /** @param {string} term */
    async fetchMessages(term) {
        term = term.trim();
        if (!term && this.searchFilter() === undefined) {
            this.searching.set(false);
            this.searched.set(false);
            this.messages.set([]);
            this.hasMore.set(false);
            this.loadMoreBeforeMessageId = undefined;
            return;
        }
        const before = this.loadMoreBeforeMessageId;
        this.loadMoreBeforeMessageId = undefined;
        const currentSearchId = ++this.searchId;
        const data = await this.store.searchMessagesInThread(
            term,
            this.thread(),
            before ?? false,
            this.searchFilter()
        );
        if (!data || currentSearchId !== this.searchId) {
            return; // Search was cleared or superseded during request.
        }
        this.searched.set(true);
        this.count.set(data.count);
        this.hasMore.set(data.loadMore);
        if (before !== undefined) {
            this.messages.set([...this.messages(), ...data.messages]);
        } else {
            this.messages.set(data.messages);
            if (!data.messages.length) {
                return false;
            }
        }
    }

    /** @param {number} beforeMessageId */
    loadMore(beforeMessageId) {
        this.loadMoreBeforeMessageId = beforeMessageId;
        this.run();
    }

    reset() {
        this.searchId++;
        super.reset();
        this.searchFilter.set(undefined);
        this.messages.set([]);
        this.searched.set(false);
        this.count.set(0);
        this.hasMore.set(false);
        this.loadMoreBeforeMessageId = undefined;
    }
}
