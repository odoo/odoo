/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { Message } from "@mail/core/common/message";
import { onWillUnmount } from "@odoo/owl";

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
     * @param {HTMLElement} element
     */
    prepareMessageBody(element) {
        const $el = $(element);
        $el.find(".o-mail-read-more-less").remove();
        this.insertReadMoreLess($el);
    },

    /**
     * Modifies the message to add the 'read more/read less' functionality
     * All element nodes with 'data-o-mail-quote' attribute are concerned.
     * All text nodes after a ``#stopSpelling`` element are concerned.
     * Those text nodes need to be wrapped in a span (toggle functionality).
     * All consecutive elements are joined in one 'read more/read less'.
     *
     * FIXME This method should be rewritten (task-2308951)
     *
     * @param {jQuery} $element
     */
    insertReadMoreLess($element) {
        const groups = [];
        let readMoreNodes;

        // nodeType 1: element_node
        // nodeType 3: text_node
        const $children = $element
            .contents()
            .filter(
                (index, content) =>
                    content.nodeType === 1 || (content.nodeType === 3 && content.nodeValue.trim())
            );

        for (const child of $children) {
            let $child = $(child);

            // Hide Text nodes if "stopSpelling"
            if (child.nodeType === 3 && $child.prevAll('[id*="stopSpelling"]').length > 0) {
                // Convert Text nodes to Element nodes
                $child = $("<span>", {
                    text: child.textContent,
                    "data-o-mail-quote": "1",
                });
                child.parentNode.replaceChild($child[0], child);
            }

            // Create array for each 'read more' with nodes to toggle
            if (
                $child.attr("data-o-mail-quote") ||
                ($child.get(0).nodeName === "BR" &&
                    $child.prev('[data-o-mail-quote="1"]').length > 0)
            ) {
                if (!readMoreNodes) {
                    readMoreNodes = [];
                    groups.push(readMoreNodes);
                }
                $child.hide();
                readMoreNodes.push($child);
            } else {
                readMoreNodes = undefined;
                this.insertReadMoreLess($child);
            }
        }

        for (const group of groups) {
            const index = this.state.lastReadMoreIndex++;
            // Insert link just before the first node
            const $readMoreLess = $("<a>", {
                class: "o-mail-read-more-less d-block",
                href: "#",
                text: "Read More",
            }).insertBefore(group[0]);

            // Toggle All next nodes
            if (!this.state.isReadMoreByIndex.has(index)) {
                this.state.isReadMoreByIndex.set(index, true);
            }
            const updateFromState = () => {
                const isReadMore = this.state.isReadMoreByIndex.get(index);
                for (const $child of group) {
                    $child.hide();
                    $child.toggle(!isReadMore);
                }
                $readMoreLess.text(isReadMore ? "Read More" : "Read Less");
            };
            $readMoreLess.click((e) => {
                e.preventDefault();
                this.state.isReadMoreByIndex.set(index, !this.state.isReadMoreByIndex.get(index));
                updateFromState();
            });
            updateFromState();
        }
    },
});
