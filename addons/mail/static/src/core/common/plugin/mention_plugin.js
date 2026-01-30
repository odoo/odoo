import { Plugin } from "@html_editor/plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { generateThreadMentionElement } from "@mail/utils/common/format";

export class MentionPlugin extends Plugin {
    static id = "mention";
    static dependencies = ["baseContainer", "selection", "history"];
    resources = {
        selectionchange_handlers: this.detectMentions.bind(this),
        is_node_editable_predicates: (node) => {
            for (const { selector } of this.MENTION_SELECTORS) {
                if (closestElement(node, selector)) {
                    return true;
                }
            }
        },
        select_all_overrides: this.selectAll.bind(this),
    };

    setup() {
        super.setup();
        /** @type {import("models").Store} */
        this.store = this.services["mail.store"];
    }

    /**
     * Extend the selection to include whole mention elements at the borders
     * so that it doesn't get stuck into the contenteditable=false
     */
    selectAll({ anchorNode, anchorOffset, focusNode, focusOffset }) {
        const SELECTOR = this.MENTION_SELECTORS.map(({ selector }) => selector).join(", ");
        if (closestElement(anchorNode, SELECTOR)) {
            const startMention = closestElement(anchorNode, SELECTOR);
            anchorNode = startMention.parentNode;
            anchorOffset = Array.prototype.indexOf.call(anchorNode.childNodes, startMention);
        }
        if (closestElement(focusNode, SELECTOR)) {
            const endMention = closestElement(focusNode, SELECTOR);
            focusNode = endMention.parentNode;
            focusOffset = Array.prototype.indexOf.call(focusNode.childNodes, endMention) + 1;
        }
        this.dependencies.selection.setSelection({
            anchorNode,
            anchorOffset,
            focusNode,
            focusOffset,
        });
    }

    get MENTION_SELECTORS() {
        return [
            {
                selector: "a.o_channel_redirect",
                checker: (el) => this.isValidChannelMentionElement(el),
                validMentionsHandler: (channelLinks) => {
                    this.store.handleValidChannelMention(channelLinks);
                    this.dependencies.history.addStep();
                },
            },
            {
                selector: "a.o_mail_redirect",
                checker: (el) => true,
            },
            {
                selector: "a.o-discuss-mention",
                checker: (el) => true,
            },
        ];
    }

    async detectMentions(ev) {
        for (const { selector, checker, validMentionsHandler } of this.MENTION_SELECTORS) {
            const mentionLinks = Array.from(this.editable.querySelectorAll(selector)) || [];
            const validMentionLinks = (
                await Promise.all(
                    mentionLinks.map(async (el) => ({
                        el,
                        isValid: await checker(el),
                    }))
                )
            )
                .filter(({ isValid }) => isValid)
                .map(({ el }) => el);
            this.prepareValidMentionLinks(validMentionLinks);
            validMentionsHandler?.(validMentionLinks);
        }
    }

    prepareValidMentionLinks(validMentionLinks) {
        for (const el of validMentionLinks) {
            // if el's parent is odoo-editor-editable, which happens when the html is computed or set with setContent,
            // considering the mention blocks are protected and not editable.
            // This will lead to issues where the mention cannot be deleted or edited properly.
            // In this case, we wrap the mention with a base container.
            if (el.parentElement === this.editable) {
                const baseContainer = this.dependencies.baseContainer.createBaseContainer();
                baseContainer.appendChild(el.cloneNode(true));
                this.editable.replaceChild(baseContainer, el);
                this.dependencies.history.addStep();
            }
        }
    }

    async isValidChannelMentionElement(el) {
        if (el.dataset.oeModel !== "discuss.channel") {
            return false;
        }
        const channel = await this.store.Thread.getOrFetch({
            model: "discuss.channel",
            id: Number(el.dataset.oeId),
        });
        if (!channel) {
            return false;
        }
        const validChannelMention = generateThreadMentionElement(channel);
        return (
            validChannelMention.getAttribute("href") === el.getAttribute("href") &&
            [...validChannelMention.classList].every((cls) => el.classList.contains(cls))
        );
    }
}
