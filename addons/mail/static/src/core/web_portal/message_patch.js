import { patch } from "@web/core/utils/patch";
import { Message } from "@mail/core/common/message";
import { onWillUnmount } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

patch(Message.prototype, {
    setup() {
        super.setup(...arguments);
        this.state.lastReadMoreIndex = 0;
        this.state.isReadMoreByIndex = new Map();
        onWillUnmount(() => {
            this.messageBody.el?.querySelector(".o-mail-read-more-less")?.remove();
        });
    },

    /**
     * @override
     * @param {HTMLElement} bodyEl
     */
    prepareMessageBody(bodyEl) {
        super.prepareMessageBody(...arguments);
        Array.from(bodyEl.querySelectorAll(".o-mail-read-more-less")).forEach((el) => el.remove());
        this.insertReadMoreLess(bodyEl);
    },

    /**
     * Modifies the message to add the 'read more/read less' functionality
     * All element nodes with 'data-o-mail-quote' attribute are concerned.
     * All text nodes after a ``#stopSpelling`` element are concerned.
     * Those text nodes need to be wrapped in a span (toggle functionality).
     * All consecutive elements are joined in one 'read more/read less'.
     *
     * @param {HTMLElement} bodyEl
     */
    insertReadMoreLess(bodyEl) {
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
        let readMoreNodes;
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
                if (!readMoreNodes) {
                    readMoreNodes = [];
                    groups.push(readMoreNodes);
                }
                hide(childEl);
                readMoreNodes.push(childEl);
            } else {
                readMoreNodes = undefined;
                this.insertReadMoreLess(childEl);
            }
        }

        for (const group of groups) {
            const index = this.state.lastReadMoreIndex++;
            // Insert link just before the first node
            const readMoreLessEl = document.createElement("a");
            readMoreLessEl.style.display = "block";
            readMoreLessEl.className = "o-mail-read-more-less";
            readMoreLessEl.href = "#";
            readMoreLessEl.textContent = _t("Read More");
            group[0].parentNode.insertBefore(readMoreLessEl, group[0]);

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
                readMoreLessEl.textContent = isReadMore
                    ? _t("Read More").toString()
                    : _t("Read Less").toString();
            };
            readMoreLessEl.addEventListener("click", (e) => {
                e.preventDefault();
                this.state.isReadMoreByIndex.set(index, !this.state.isReadMoreByIndex.get(index));
                updateFromState();
            });
            updateFromState();
        }
    },
});
