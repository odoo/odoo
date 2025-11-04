import { Plugin } from "@html_editor/plugin";
import { generateThreadMentionElement } from "@mail/utils/common/format";

export class MentionPlugin extends Plugin {
    static id = "mention";
    static dependencies = ["selection", "history"];
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
            validMentionsHandler?.(validMentionLinks);
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
