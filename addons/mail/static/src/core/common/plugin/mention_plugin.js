import { Plugin } from "@html_editor/plugin";
import { generateThreadMentionElement } from "@mail/utils/common/format";

export class MentionPlugin extends Plugin {
    static id = "mention";
    static dependencies = ["baseContainer", "selection", "history", "protectedNode"];
    resources = {
        selectionchange_handlers: this.detectMentions.bind(this),
    };

    setup() {
        super.setup();
        /** @type {import("models").Store} */
        this.store = this.services["mail.store"];
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
                checker: () => true,
            },
            {
                selector: "a.o-discuss-mention",
                checker: () => true,
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
            this.dependencies.protectedNode.setProtectingNode(el, true);
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
