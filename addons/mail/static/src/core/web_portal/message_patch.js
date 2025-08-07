import { patch } from "@web/core/utils/patch";
import { Message } from "@mail/core/common/message";
import { onWillUnmount } from "@odoo/owl";

patch(Message.prototype, {
    setup() {
        super.setup(...arguments);
        this.state.lastReadMoreIndex = 0;
        this.state.isReadMoreByIndex = new Map();
        onWillUnmount(() => {
            this.messageBody.el?.querySelector(".o-mail-ellipsis")?.remove();
        });
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
     * Modifies the message to add the 'ellipsis button' functionality
     * All element nodes with 'data-o-mail-quote' attribute are concerned.
     * All text nodes after a ``#stopSpelling`` element are concerned.
     * Those text nodes need to be wrapped in a span (toggle functionality).
     * All consecutive elements are joined in one 'ellipsis button'.
     *
     * @param {HTMLElement} bodyEl
     */
    insertEllipsisbtn(bodyEl) {
        /**
         * @param {HTMLElement} e
         * @param {string} selector
         */
        function prevAll(e, selector) {
            const res = [];
            while ((e = e.previousElementSibling)) {
                if (e.matches(selector)) {
                    res.push(e);
                }
            }
            return res;
        }

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
            if (
                childEl.nodeType === TEXT_NODE &&
                prevAll(childEl, '[id*="stopSpelling"]').length > 0
            ) {
                // Convert Text nodes to Element nodes
                const newChildEl = document.createElement("span");
                newChildEl.textContent = childEl.textContent;
                newChildEl.dataset.oMailQuote = "1";
                childEl.parentNode.replaceChild(newChildEl, childEl);
            }
            // Create array for each 'read more' with nodes to toggle
            if (
                (childEl.nodeType === ELEMENT_NODE && childEl.getAttribute("data-o-mail-quote")) ||
                (childEl.nodeName === "BR" && prev(childEl, '[data-o-mail-quote="1"]'))
            ) {
                if (!ellipsisNodes) {
                    ellipsisNodes = [];
                    groups.push(ellipsisNodes);
                }
                hide(childEl);
                ellipsisNodes.push(childEl);
            } else {
                ellipsisNodes = undefined;
                this.insertEllipsisbtn(childEl);
            }
        }

        for (const group of groups) {
            const index = this.state.lastReadMoreIndex++;
            const ellipsisbtnEl = document.createElement("button");
            ellipsisbtnEl.className = "o-mail-ellipsis badge rounded-pill border-0 py-0 px-1";
            const iconellipsisEl = document.createElement("i");
            iconellipsisEl.className = "oi oi-ellipsis-h oi-large";
            ellipsisbtnEl.append(iconellipsisEl);
            group[0].parentNode.insertBefore(ellipsisbtnEl, group[0]);
            // Toggle all nodes except reply nodes
            if (!this.state.isReadMoreByIndex.has(index) && !group[0].querySelector('.o_mail_reply_content')) {
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
        }
    },
});
