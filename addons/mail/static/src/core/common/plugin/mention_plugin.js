import { Plugin } from "@html_editor/plugin";

export class MentionPlugin extends Plugin {
    static id = "mention";
    static dependencies = ["baseContainer", "selection", "history"];
    resources = {
        on_selectionchange_handlers: this.detectMentions.bind(this),
        selectors_for_feff_providers: () =>
            this.MENTION_SELECTORS.map(({ selector }) => selector).join(", "),
    };

    get MENTION_SELECTORS() {
        return [
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
                const baseContainer = this.dependencies.baseContainer.createBaseContainer({
                    children: [el.cloneNode(true)],
                });
                this.editable.replaceChild(baseContainer, el);
                this.dependencies.history.commit();
            }
        }
    }
}
