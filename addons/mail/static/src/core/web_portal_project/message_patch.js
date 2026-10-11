import { patch } from "@web/core/utils/patch";
import { Message } from "@mail/core/common/message";

const REPLY_ATTRIBUTION_SELECTOR =
    ".gmail_attr, .o_mail_reply_container > .o_mail_reply_content > div:first-child";

/**
 * @param {HTMLElement} e
 * @param {string} selector
 */
function prev(e, selector) {
    while ((e = e.previousElementSibling)) {
        if (e.matches(selector)) {
            return e;
        }
    }
}

/** @param {HTMLElement} el */
function hide(el) {
    el.dataset.oMailDisplay = el.style.display;
    el.style.display = "none";
}

/**
 * @param {HTMLElement} el
 * @param {boolean} condition
 */
function toggle(el, condition = false) {
    if (condition) {
        let newDisplay = el.dataset.oMailDisplay;
        if (newDisplay === "none") {
            newDisplay = null;
        }
        el.style.display = newDisplay;
    } else {
        hide(el);
    }
}

// Attribution headers belong to the quote they introduce, rather than
// representing another reply level. Stop at blockquotes to avoid scanning
// the entire nested history when checking a wrapper's own content.
function hasOwnReplyContent(el) {
    return Array.from(el.childNodes).some((node) => {
        if (node.nodeType === Node.TEXT_NODE) {
            return Boolean(node.textContent.trim());
        }
        if (node.nodeType !== Node.ELEMENT_NODE) {
            return false;
        }
        if (node.matches("blockquote") || node.matches(REPLY_ATTRIBUTION_SELECTOR)) {
            return false;
        }
        return node.matches("img, video, audio, hr") || hasOwnReplyContent(node);
    });
}

patch(Message.prototype, {
    setup() {
        super.setup(...arguments);
        this.state.lastReadMoreIndex = 0;
        this.state.isReadMoreByIndex = new Map();
    },

    /**
     * @override
     * @param {HTMLElement} bodyEl
     */
    prepareMessageBody(bodyEl) {
        if (!bodyEl) {
            return;
        }
        super.prepareMessageBody(...arguments);
        Array.from(bodyEl.querySelectorAll(".o-mail-ellipsis")).forEach((el) => el.remove());
        this.insertEllipsisbtn(bodyEl);
    },

    /**
     * Hide consecutive quoted elements behind one button. Within a quote, only
     * blockquotes start another level; inherited paragraph markers do not.
     * @param {HTMLElement} bodyEl
     */
    insertEllipsisbtn(bodyEl) {
        // Quote markers on ancestors identify history; markers inherited by its
        // paragraphs must not create additional reply levels.
        const insideQuote =
            bodyEl.nodeType === Node.ELEMENT_NODE && bodyEl.closest("[data-o-mail-quote]");
        const groups = [];
        let ellipsisNodes;
        const ELEMENT_NODE = 1;
        const TEXT_NODE = 3;
        /** @type {ChildNode[]} childrenEl */
        const childrenEl = Array.from(bodyEl.childNodes).filter(
            /** @param {ChildNode} childEl */
            function (childEl) {
                return (
                    childEl.nodeType === ELEMENT_NODE ||
                    (childEl.nodeType === TEXT_NODE && childEl.nodeValue.trim())
                );
            }
        );
        for (const childEl of childrenEl) {
            // Hide Text nodes if "stopSpelling"
            if (childEl.nodeType === TEXT_NODE && prev(childEl, '[id*="stopSpelling"]')) {
                // Convert Text nodes to Element nodes
                const newChildEl = document.createElement("span");
                newChildEl.textContent = childEl.textContent;
                newChildEl.dataset.oMailQuote = "1";
                childEl.parentNode.replaceChild(newChildEl, childEl);
            }
            // Create array for each 'read more' with nodes to toggle
            const isQuote =
                childEl.nodeType === ELEMENT_NODE &&
                (insideQuote
                    ? childEl.matches("blockquote[data-o-mail-quote]")
                    : childEl.matches("[data-o-mail-quote]") ||
                      (childEl.nodeName === "BR" && prev(childEl, '[data-o-mail-quote="1"]')));
            if (isQuote) {
                if (!ellipsisNodes) {
                    ellipsisNodes = [];
                    groups.push(ellipsisNodes);
                }
                // Inherited quote markers on paragraphs are not reply boundaries.
                // Skip a wrapper's blockquote only when the wrapper has no reply
                // content of its own (apart from the mail client's attribution).
                if (childEl.matches("blockquote") || hasOwnReplyContent(childEl)) {
                    this.insertEllipsisbtn(childEl);
                } else {
                    const quotes = Array.from(childEl.querySelectorAll("blockquote")).filter(
                        (quote) => !childEl.contains(quote.parentElement.closest("blockquote"))
                    );
                    for (const quote of quotes) {
                        this.insertEllipsisbtn(quote);
                    }
                }
                hide(childEl);
                ellipsisNodes.push(childEl);
            } else {
                ellipsisNodes = undefined;
                this.insertEllipsisbtn(childEl);
            }
        }

        for (const group of groups) {
            this.insertQuoteButton(group);
        }
    },

    /** @param {HTMLElement[]} group Consecutive quoted elements sharing a button. */
    insertQuoteButton(group) {
        const index = this.state.lastReadMoreIndex++;
        const ellipsisbtnEl = document.createElement("button");
        ellipsisbtnEl.className = "o-mail-ellipsis badge rounded-pill border-0 py-0 px-1";
        const iconellipsisEl = document.createElement("i");
        iconellipsisEl.className = "oi oi-lg";
        iconellipsisEl.dataset.icon = "more_horiz";
        ellipsisbtnEl.append(iconellipsisEl);
        group[0].parentNode.insertBefore(ellipsisbtnEl, group[0]);
        // Toggle All next nodes
        if (!this.state.isReadMoreByIndex.has(index)) {
            this.state.isReadMoreByIndex.set(index, true);
        }
        const updateFromState = () => {
            const isReadMore = this.state.isReadMoreByIndex.get(index);
            for (const childEl of group) {
                hide(childEl);
                toggle(childEl, !isReadMore);
            }
        };
        ellipsisbtnEl.addEventListener("click", (e) => {
            e.preventDefault();
            this.state.isReadMoreByIndex.set(index, !this.state.isReadMoreByIndex.get(index));
            updateFromState();
        });
        updateFromState();
    },
});
